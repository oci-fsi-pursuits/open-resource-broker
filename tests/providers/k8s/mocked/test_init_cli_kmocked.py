"""``orb init`` for Kubernetes through the real CLI entry point, against a kmock apiserver.

The kubeconfig is read from ``$HOME/.kube/config`` exactly as for a user; only the
cluster is emulated.  kmock cannot parse cluster-scoped list paths or answer
self-subject access reviews, so those two calls are stubbed on the SDK API class.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import kmock
import pytest

_KUBECONFIG = """\
apiVersion: v1
kind: Config
current-context: ctx
clusters:
- name: cluster
  cluster:
    server: {server}
contexts:
- name: ctx
  context:
    cluster: cluster
    user: user
users:
- name: user
  user:
    token: static-token
"""


@pytest.mark.asyncio
async def test_cli_init_writes_k8s_config_and_loads_kubeconfig_once(
    kmock_k8s, tmp_path, monkeypatch
) -> None:
    import kubernetes.config
    from kubernetes.client import AuthorizationV1Api, CoreV1Api
    from kubernetes.client.api_client import ApiClient

    from tests.utilities.init_flow import run_cli_init

    kube_dir = tmp_path / ".kube"
    kube_dir.mkdir()
    (kube_dir / "config").write_text(_KUBECONFIG.format(server=str(kmock_k8s.url).rstrip("/")))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("KUBECONFIG", raising=False)
    # The default location is computed at import time from the shell's KUBECONFIG.
    monkeypatch.setattr(
        kubernetes.config.kube_config, "KUBE_CONFIG_DEFAULT_LOCATION", str(kube_dir / "config")
    )

    _ = kmock_k8s["get /api/v1/"] << {
        "kind": "APIResourceList",
        "groupVersion": "v1",
        "resources": [],
    }
    kmock_k8s.objects[kmock.resource("", "v1", "serviceaccounts"), "default", "orb"] = {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {"name": "orb", "namespace": "default"},
    }
    kmock_k8s.objects[kmock.resource("", "v1", "secrets"), "default", "registry"] = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "registry", "namespace": "default"},
        "type": "kubernetes.io/dockerconfigjson",
    }
    namespace = SimpleNamespace(
        metadata=SimpleNamespace(name="default", creation_timestamp=None),
        status=SimpleNamespace(phase="Active"),
    )
    allowed = SimpleNamespace(status=SimpleNamespace(allowed=True, reason=""))

    with (
        patch.object(CoreV1Api, "list_namespace", return_value=SimpleNamespace(items=[namespace])),
        patch.object(AuthorizationV1Api, "create_self_subject_access_review", return_value=allowed),
        patch.object(
            kubernetes.config, "load_kube_config", wraps=kubernetes.config.load_kube_config
        ) as load,
        patch.object(ApiClient, "__init__", autospec=True, side_effect=ApiClient.__init__) as built,
    ):
        code, config = await asyncio.to_thread(run_cli_init, "k8s", tmp_path)

    assert code == 0
    (provider,) = config["provider"]["providers"]
    assert provider["type"] == "k8s"
    assert provider["config"] == {"context": "ctx", "namespace": "default", "in_cluster": False}
    assert config["provider"]["default_provider_instance"] == provider["name"]
    load.assert_called_once()
    built.assert_called_once()
    assert any("/namespaces/default/serviceaccounts" in str(request.url) for request in kmock_k8s)
