"""The shared kubeconfig ApiClient keeps authenticating after its exec token expires.

The kubeconfig points at an ``exec`` credential plugin that mints ``tok-N`` with a
short expiry.  The apiserver stub rejects every token that has been retired, so a
client that froze its first token fails with 401 once the token lapses.  Only the
SDK's expiry clock is replaced; the plugin is a real subprocess.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import shlex
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import kmock
import pytest
import pytest_asyncio

from orb.providers.k8s.auth.kubeconfig import get_shared_api_client

_LIFETIME_SECONDS = 3600
_NAMESPACE = "orb-test"

_PLUGIN_SCRIPT = """\
import datetime
import json
import sys
from pathlib import Path

state = Path(sys.argv[1])
counter = state / "counter"
count = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(count))
offset = int((state / "offset").read_text()) if (state / "offset").exists() else 0
expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
    seconds=offset + {lifetime}
)
print(
    json.dumps(
        {{
            "apiVersion": "client.authentication.k8s.io/v1",
            "kind": "ExecCredential",
            "status": {{
                "token": f"tok-{{count}}",
                "expirationTimestamp": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }},
        }}
    )
)
"""


class _ExecPlugin:
    """Handle on the credential plugin's on-disk state and the shared fake clock."""

    def __init__(self, state: Path, kubeconfig: Path, real_datetime: types.ModuleType) -> None:
        self.state = state
        self.kubeconfig = kubeconfig
        self._real_datetime = real_datetime
        self.offset = datetime.timedelta()

    @property
    def runs(self) -> int:
        counter = self.state / "counter"
        return int(counter.read_text()) if counter.exists() else 0

    def now(self, tz=None) -> datetime.datetime:
        return self._real_datetime.datetime.now(tz) + self.offset

    def advance(self, seconds: int) -> None:
        """Move the SDK clock forward; the plugin issues expiries on the same timeline."""
        self.offset += datetime.timedelta(seconds=seconds)
        (self.state / "offset").write_text(str(int(self.offset.total_seconds())))


@pytest_asyncio.fixture()
async def stub(kmock_k8s, tmp_path, monkeypatch) -> _ExecPlugin:
    """An apiserver with one pod, a kubeconfig using the exec plugin, and a fake SDK clock."""
    from kubernetes.config import kube_config

    kmock_k8s.objects[kmock.resource("", "v1", "pods"), _NAMESPACE, "p"] = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "p", "namespace": _NAMESPACE},
        "spec": {"containers": [{"name": "app", "image": "busybox"}]},
    }

    state = tmp_path / "state"
    state.mkdir()
    script = tmp_path / "exec_plugin.py"
    script.write_text(_PLUGIN_SCRIPT.format(lifetime=_LIFETIME_SECONDS))
    kubeconfig = tmp_path / "kubeconfig"
    kubeconfig.write_text(
        f"""\
apiVersion: v1
kind: Config
current-context: ctx
clusters:
- name: cluster
  cluster:
    server: {str(kmock_k8s.url).rstrip("/")}
contexts:
- name: ctx
  context:
    cluster: cluster
    user: user
users:
- name: user
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1
      command: {shlex.quote(sys.executable)}
      args: {json.dumps([str(script), str(state)])}
      interactiveMode: Never
"""
    )

    plugin = _ExecPlugin(state, kubeconfig, datetime)

    class _FakeDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return plugin.now(tz)

    clock = types.ModuleType("datetime")
    clock.__dict__.update(datetime.__dict__)
    clock.datetime = _FakeDatetime
    monkeypatch.setattr(kube_config, "datetime", clock)
    return plugin


def _reject(apiserver, token: str) -> None:
    """Make the apiserver answer 401 to ``token`` from now on."""
    apiserver[kmock.headers({"Authorization": f"Bearer {token}"})] << 401


def _list_pods(api_client) -> list[str]:
    import kubernetes.client as kc

    pods = kc.CoreV1Api(api_client).list_namespaced_pod(_NAMESPACE)
    return [pod.metadata.name for pod in pods.items]


def _bearers(apiserver) -> list[str]:
    return [request.headers.get("Authorization", "") for request in apiserver]


@pytest.mark.asyncio
async def test_shared_api_client_mints_a_new_token_after_expiry(kmock_k8s, stub) -> None:
    client = await asyncio.to_thread(get_shared_api_client, config_file=str(stub.kubeconfig))
    assert stub.runs == 1

    assert await asyncio.to_thread(_list_pods, client) == ["p"]
    assert await asyncio.to_thread(_list_pods, client) == ["p"]
    assert stub.runs == 1

    stub.advance(2 * _LIFETIME_SECONDS)
    _reject(kmock_k8s, "tok-1")

    assert await asyncio.to_thread(_list_pods, client) == ["p"]

    assert stub.runs == 2
    assert _bearers(kmock_k8s) == ["Bearer tok-1", "Bearer tok-1", "Bearer tok-2"]
    assert get_shared_api_client(config_file=str(stub.kubeconfig)) is client
    assert stub.runs == 2


@pytest.mark.asyncio
async def test_shared_api_client_does_not_remint_while_the_token_is_valid(kmock_k8s, stub) -> None:
    client = await asyncio.to_thread(get_shared_api_client, config_file=str(stub.kubeconfig))

    stub.advance(_LIFETIME_SECONDS // 2)

    assert await asyncio.to_thread(_list_pods, client) == ["p"]
    assert stub.runs == 1
    assert _bearers(kmock_k8s) == ["Bearer tok-1"]


@pytest.mark.asyncio
async def test_force_token_refresh_recovers_when_the_server_revokes_a_live_token(
    kmock_k8s, stub, monkeypatch
) -> None:
    """A token revoked before its expiry is recovered by the runtime client's 401 path."""
    import kubernetes.client as kc

    from orb.providers.k8s.configuration.config import K8sProviderConfig
    from orb.providers.k8s.infrastructure.k8s_client import K8sClient

    # The plugin is the test interpreter, which is not on the well-known plugin list.
    monkeypatch.setenv("ORB_K8S_ALLOW_UNKNOWN_EXEC_PLUGIN", "1")
    config = K8sProviderConfig(  # type: ignore[call-arg]
        namespace=_NAMESPACE, in_cluster=False, kubeconfig_path=str(stub.kubeconfig)
    )
    client = K8sClient(config=config, logger=MagicMock())
    await asyncio.to_thread(lambda: client.api_client)
    assert stub.runs == 1

    _reject(kmock_k8s, "tok-1")

    with pytest.raises(kc.ApiException) as denied:
        await asyncio.to_thread(client.core_v1.list_namespaced_pod, _NAMESPACE)
    assert denied.value.status == 401

    assert await asyncio.to_thread(client.force_token_refresh) is True
    pods = await asyncio.to_thread(client.core_v1.list_namespaced_pod, _NAMESPACE)

    assert [pod.metadata.name for pod in pods.items] == ["p"]
    assert stub.runs == 2
    assert _bearers(kmock_k8s)[-1] == "Bearer tok-2"


@pytest.mark.asyncio
async def test_discovery_recovers_on_the_next_step_after_the_server_revokes_a_live_token(
    kmock_k8s, stub, monkeypatch
) -> None:
    """A 401 during discovery drops the cached client so the next step reloads credentials."""
    from orb.providers.k8s.configuration.config import K8sProviderConfig
    from orb.providers.k8s.exceptions import K8sDiscoveryError
    from orb.providers.k8s.services.infrastructure_discovery_service import (
        K8sInfrastructureDiscoveryService,
    )

    monkeypatch.setattr(
        "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
        lambda: False,
    )
    config = K8sProviderConfig(  # type: ignore[call-arg]
        namespace=_NAMESPACE, in_cluster=False, kubeconfig_path=str(stub.kubeconfig)
    )
    service = K8sInfrastructureDiscoveryService(config=config, logger=MagicMock())
    kmock_k8s.resources[kmock.resource("", "v1", "serviceaccounts")] = {}

    await asyncio.to_thread(service.discover_service_accounts, _NAMESPACE)
    assert stub.runs == 1

    _reject(kmock_k8s, "tok-1")

    with pytest.raises(K8sDiscoveryError):
        await asyncio.to_thread(service.discover_service_accounts, _NAMESPACE)

    assert await asyncio.to_thread(service.discover_service_accounts, _NAMESPACE) == []

    assert stub.runs == 2
    assert _bearers(kmock_k8s)[-1] == "Bearer tok-2"
