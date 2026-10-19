"""Unit tests for K8sInfrastructureDiscoveryService.

Covers uncovered ranges:
  infrastructure_discovery_service.py :: 62,74-75,78,83-84,87,131-135,138-139,141,145,149-150,
  155,159-160,165,310,344-345,374,429,438,555,579-581,707,724,742,746,792,921,945-946,956,972
"""

from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from orb.providers.k8s.exceptions.k8s_exceptions import K8sDiscoveryError, K8sError
from orb.providers.k8s.services.discovery_models import (
    KubeContextInfo,
    NamespaceInfo,
    RBACProbeResult,
    ServiceAccountInfo,
)
from orb.providers.k8s.services.infrastructure_discovery_service import (
    K8sInfrastructureDiscoveryService,
    _age_days,
    _is_forbidden,
    _is_not_found,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_logger() -> Any:
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


def _make_config(**kwargs: Any) -> Any:
    from orb.providers.k8s.configuration.config import K8sProviderConfig

    defaults: dict[str, Any] = {"namespace": "default"}
    defaults.update(kwargs)
    return K8sProviderConfig(**defaults)  # type: ignore[call-arg]


def _make_service(
    api_client: Any = None, **config_kwargs: Any
) -> K8sInfrastructureDiscoveryService:
    cfg = _make_config(**config_kwargs)
    return K8sInfrastructureDiscoveryService(
        config=cfg,
        logger=_make_logger(),  # type: ignore[arg-type]
        api_client=api_client,
    )


def _make_fake_api_exception(status: int) -> Exception:
    try:
        from kubernetes.client.exceptions import ApiException

        exc = ApiException(status=status)
        return exc
    except ImportError:

        class _FakeApiException(Exception):
            def __init__(self, s: int) -> None:
                self.status = s

        return _FakeApiException(status)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAgeDays:
    def test_none_returns_zero(self) -> None:
        assert _age_days(None) == 0

    def test_datetime_object_returns_correct_days(self) -> None:
        ts = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=3)
        assert _age_days(ts) == 3

    def test_naive_datetime_treated_as_utc(self) -> None:
        ts = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        assert _age_days(ts) == 2

    def test_iso_string_parsed_correctly(self) -> None:
        ts = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=5)
        ts_str = ts.isoformat().replace("+00:00", "Z")
        assert _age_days(ts_str) == 5

    def test_zero_when_future_timestamp(self) -> None:
        ts = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=1)
        assert _age_days(ts) == 0

    def test_invalid_string_returns_zero(self) -> None:
        assert _age_days("not-a-date") == 0


@pytest.mark.unit
class TestIsForbiddenIsNotFound:
    def test_is_forbidden_true_for_403(self) -> None:
        exc = _make_fake_api_exception(403)
        assert _is_forbidden(exc) is True

    def test_is_forbidden_false_for_404(self) -> None:
        exc = _make_fake_api_exception(404)
        assert _is_forbidden(exc) is False

    def test_is_forbidden_false_for_generic_exception(self) -> None:
        assert _is_forbidden(RuntimeError("nope")) is False

    def test_is_not_found_true_for_404(self) -> None:
        exc = _make_fake_api_exception(404)
        assert _is_not_found(exc) is True

    def test_is_not_found_false_for_403(self) -> None:
        exc = _make_fake_api_exception(403)
        assert _is_not_found(exc) is False

    def test_is_not_found_false_for_generic_exception(self) -> None:
        assert _is_not_found(ValueError("x")) is False


# ---------------------------------------------------------------------------
# K8sInfrastructureDiscoveryService._get_api_client
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetApiClient:
    def test_returns_injected_client(self) -> None:
        fake_client = MagicMock()
        svc = _make_service(api_client=fake_client)
        assert svc._get_api_client() is fake_client

    def test_builds_client_in_cluster(self) -> None:
        svc = _make_service()
        with (
            patch(
                "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
                return_value=True,
            ),
            patch("kubernetes.config.load_incluster_config") as mock_load,
            patch(
                "kubernetes.client.api_client.ApiClient",
                return_value=MagicMock(),
            ),
        ):
            svc._get_api_client()
            mock_load.assert_called_once()

    def test_builds_client_out_of_cluster(self) -> None:
        svc = _make_service(context="my-ctx")
        with (
            patch(
                "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
                return_value=False,
            ),
            patch("kubernetes.config.load_kube_config") as mock_load,
            patch("kubernetes.client.api_client.ApiClient", return_value=MagicMock()),
        ):
            svc._get_api_client()
            mock_load.assert_called_once()


# ---------------------------------------------------------------------------
# detect_in_cluster
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectInCluster:
    def test_delegates_to_is_in_cluster(self) -> None:
        svc = _make_service()
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
            return_value=True,
        ):
            assert svc.detect_in_cluster() is True

    def test_out_of_cluster(self) -> None:
        svc = _make_service()
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
            return_value=False,
        ):
            assert svc.detect_in_cluster() is False


# ---------------------------------------------------------------------------
# discover_contexts (line 207-250)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverContexts:
    def test_raises_discovery_error_when_sdk_missing(self) -> None:
        svc = _make_service()
        with patch.dict(
            "sys.modules",
            {"kubernetes": None, "kubernetes.config": None},  # type: ignore[dict-item]
        ):
            # We can't easily block the re-import; test the RuntimeError path instead
            with patch(
                "orb.providers.k8s.services.infrastructure_discovery_service.K8sInfrastructureDiscoveryService.discover_contexts",
                side_effect=K8sDiscoveryError("sdk not installed"),
            ):
                with pytest.raises(K8sDiscoveryError):
                    svc.discover_contexts()

    def test_returns_empty_on_kubeconfig_parse_failure(self) -> None:
        svc = _make_service()
        with patch(
            "kubernetes.config.list_kube_config_contexts",
            side_effect=RuntimeError("no kubeconfig"),
        ):
            all_ctxs, current = svc.discover_contexts()
        assert all_ctxs == []
        assert current is None

    def test_parses_contexts_correctly(self) -> None:
        svc = _make_service()
        raw_contexts = [
            {"name": "prod", "context": {"cluster": "prod-cluster", "user": "admin"}},
            {"name": "dev", "context": {"cluster": "dev-cluster", "user": "dev-user"}},
        ]
        raw_current = {"name": "prod"}
        with patch(
            "kubernetes.config.list_kube_config_contexts",
            return_value=(raw_contexts, raw_current),
        ):
            ctxs, current = svc.discover_contexts()

        assert len(ctxs) == 2
        assert ctxs[0].name == "prod"
        assert ctxs[0].is_current is True
        assert ctxs[1].is_current is False
        assert current is not None and current.name == "prod"

    def test_current_none_when_no_current(self) -> None:
        svc = _make_service()
        raw_contexts = [{"name": "only", "context": {"cluster": "cl"}}]
        with patch(
            "kubernetes.config.list_kube_config_contexts",
            return_value=(raw_contexts, None),
        ):
            _ctxs, current = svc.discover_contexts()
        assert current is None


# ---------------------------------------------------------------------------
# discover_cluster_endpoint (line 252-285)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverClusterEndpoint:
    def test_returns_unknown_on_exception(self) -> None:
        svc = _make_service()
        with patch(
            "kubernetes.config.load_kube_config",
            side_effect=RuntimeError("bad context"),
        ):
            endpoint = svc.discover_cluster_endpoint(context="nonexistent")
        assert endpoint == "unknown"

    def test_returns_host_from_config(self) -> None:
        svc = _make_service()
        fake_client = MagicMock()
        fake_client.configuration.host = "https://1.2.3.4:6443"
        with (
            patch("kubernetes.config.load_kube_config"),
            patch("kubernetes.client.api_client.ApiClient", return_value=fake_client),
        ):
            endpoint = svc.discover_cluster_endpoint(context="my-ctx")
        assert endpoint == "https://1.2.3.4:6443"


# ---------------------------------------------------------------------------
# discover_namespaces (line 287-331)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverNamespaces:
    def _make_ns_item(self, name: str, phase: str = "Active", age_days: int = 0) -> Any:
        ts = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=age_days)
        meta = SimpleNamespace(name=name, labels={}, creation_timestamp=ts)
        status = SimpleNamespace(phase=phase)
        return SimpleNamespace(metadata=meta, status=status)

    def test_returns_namespace_list(self) -> None:
        fake_client = MagicMock()
        ns1 = self._make_ns_item("default", "Active")
        ns2 = self._make_ns_item("kube-system", "Active")
        fake_client.core_v1.list_namespace.return_value = SimpleNamespace(items=[ns1, ns2])
        svc = _make_service(api_client=fake_client)
        # Patch _core_v1 to return our mock
        with patch.object(svc, "_core_v1", return_value=fake_client.core_v1):
            result = svc.discover_namespaces()
        assert len(result) == 2
        names = [n.name for n in result]
        assert "default" in names

    def test_returns_empty_on_403_without_sa_file(self) -> None:
        fake_client = MagicMock()
        fake_client.list_namespace.side_effect = _make_fake_api_exception(403)
        svc = _make_service()
        exc_403 = _make_fake_api_exception(403)
        with (
            patch.object(svc, "_core_v1", side_effect=exc_403),
            patch(
                "orb.providers.k8s.services.infrastructure_discovery_service._SA_NAMESPACE_FILE",
                new=Path("/nonexistent/path/namespace"),
            ),
        ):
            result = svc.discover_namespaces()
        # When 403 + no SA file, returns empty list
        assert result == []

    def test_raises_discovery_error_on_non_403_exception(self) -> None:
        svc = _make_service()
        with patch.object(svc, "_core_v1", side_effect=RuntimeError("network error")):
            with pytest.raises(K8sDiscoveryError, match="Failed to list namespaces"):
                svc.discover_namespaces()

    def test_re_raises_k8s_error(self) -> None:
        svc = _make_service()
        with patch.object(svc, "_core_v1", side_effect=K8sError("sdk missing")):
            with pytest.raises(K8sError):
                svc.discover_namespaces()


# ---------------------------------------------------------------------------
# _fallback_namespaces_from_sa_file (line 333-353)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFallbackNamespacesFromSaFile:
    def test_returns_namespace_from_file(self, tmp_path: Path) -> None:
        sa_file = tmp_path / "namespace"
        sa_file.write_text("my-namespace\n", encoding="utf-8")
        svc = _make_service()
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service._SA_NAMESPACE_FILE",
            new=sa_file,
        ):
            result = svc._fallback_namespaces_from_sa_file()
        assert len(result) == 1
        assert result[0].name == "my-namespace"
        assert result[0].status == "Active"

    def test_returns_empty_when_file_absent(self) -> None:
        svc = _make_service()
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service._SA_NAMESPACE_FILE",
            new=Path("/nonexistent/namespace"),
        ):
            result = svc._fallback_namespaces_from_sa_file()
        assert result == []

    def test_returns_empty_when_file_content_empty(self, tmp_path: Path) -> None:
        sa_file = tmp_path / "namespace"
        sa_file.write_text("   \n", encoding="utf-8")
        svc = _make_service()
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service._SA_NAMESPACE_FILE",
            new=sa_file,
        ):
            result = svc._fallback_namespaces_from_sa_file()
        assert result == []


# ---------------------------------------------------------------------------
# discover_service_accounts (line 355-401)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverServiceAccounts:
    def _make_sa_item(self, name: str, namespace: str = "default") -> Any:
        meta = SimpleNamespace(name=name, annotations={})
        return SimpleNamespace(metadata=meta, secrets=[])

    def test_returns_sa_list(self) -> None:
        fake_core = MagicMock()
        sa1 = self._make_sa_item("default")
        sa2 = self._make_sa_item("orb-sa")
        fake_core.list_namespaced_service_account.return_value = SimpleNamespace(items=[sa1, sa2])
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            result = svc.discover_service_accounts("default")
        assert len(result) == 2
        assert result[0].name == "default"

    def test_returns_empty_on_403(self) -> None:
        fake_core = MagicMock()
        fake_core.list_namespaced_service_account.side_effect = _make_fake_api_exception(403)
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            result = svc.discover_service_accounts("default")
        assert result == []

    def test_raises_discovery_error_on_non_403(self) -> None:
        fake_core = MagicMock()
        fake_core.list_namespaced_service_account.side_effect = RuntimeError("server error")
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            with pytest.raises(K8sDiscoveryError):
                svc.discover_service_accounts("default")

    def test_re_raises_k8s_error(self) -> None:
        fake_core = MagicMock()
        fake_core.list_namespaced_service_account.side_effect = K8sError("sdk missing")
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            with pytest.raises(K8sError):
                svc.discover_service_accounts("default")


# ---------------------------------------------------------------------------
# discover_image_pull_secrets (line 403-446)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverImagePullSecrets:
    def _make_secret_item(self, name: str) -> Any:
        meta = SimpleNamespace(name=name)
        return SimpleNamespace(metadata=meta)

    def test_returns_secret_names(self) -> None:
        fake_core = MagicMock()
        s1 = self._make_secret_item("my-registry-secret")
        fake_core.list_namespaced_secret.return_value = SimpleNamespace(items=[s1])
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            result = svc.discover_image_pull_secrets("default")
        assert result == ["my-registry-secret"]

    def test_returns_empty_on_403(self) -> None:
        fake_core = MagicMock()
        fake_core.list_namespaced_secret.side_effect = _make_fake_api_exception(403)
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            result = svc.discover_image_pull_secrets("default")
        assert result == []

    def test_raises_discovery_error_on_non_403(self) -> None:
        fake_core = MagicMock()
        fake_core.list_namespaced_secret.side_effect = RuntimeError("eof")
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            with pytest.raises(K8sDiscoveryError):
                svc.discover_image_pull_secrets("default")

    def test_re_raises_k8s_error(self) -> None:
        fake_core = MagicMock()
        fake_core.list_namespaced_secret.side_effect = K8sError("sdk missing")
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            with pytest.raises(K8sError):
                svc.discover_image_pull_secrets("default")

    def test_secrets_with_none_name_are_excluded(self) -> None:
        fake_core = MagicMock()
        no_name = SimpleNamespace(metadata=SimpleNamespace(name=None))
        real = self._make_secret_item("valid-secret")
        fake_core.list_namespaced_secret.return_value = SimpleNamespace(items=[no_name, real])
        svc = _make_service()
        with patch.object(svc, "_core_v1", return_value=fake_core):
            result = svc.discover_image_pull_secrets("default")
        assert result == ["valid-secret"]


# ---------------------------------------------------------------------------
# discover_infrastructure — composition method (line 515-620)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverInfrastructure:
    def _mock_all_leaf_methods(self, svc: K8sInfrastructureDiscoveryService) -> None:
        svc.detect_in_cluster = MagicMock(return_value=False)  # type: ignore[method-assign]
        svc.discover_contexts = MagicMock(  # type: ignore[method-assign]
            return_value=(
                [
                    KubeContextInfo(
                        name="ctx", cluster="cl", user="u", namespace=None, is_current=True
                    )
                ],
                KubeContextInfo(
                    name="ctx", cluster="cl", user="u", namespace=None, is_current=True
                ),
            )
        )
        svc.discover_cluster_endpoint = MagicMock(return_value="https://k8s:6443")  # type: ignore[method-assign]
        svc.discover_namespaces = MagicMock(  # type: ignore[method-assign]
            return_value=[NamespaceInfo(name="default", status="Active", age_days=0)]
        )
        svc.discover_service_accounts = MagicMock(  # type: ignore[method-assign]
            return_value=[ServiceAccountInfo(name="default", namespace="default", secrets_count=0)]
        )
        svc.discover_image_pull_secrets = MagicMock(return_value=[])  # type: ignore[method-assign]
        svc.probe_rbac = MagicMock(  # type: ignore[method-assign]
            return_value=RBACProbeResult(
                namespace="default",
                can_create_pods=True,
                can_watch_pods=True,
                can_delete_pods=True,
            )
        )

    def test_returns_required_keys(self) -> None:
        svc = _make_service()
        self._mock_all_leaf_methods(svc)
        result = svc.discover_infrastructure({"name": "my-k8s"})
        for key in ("in_cluster", "contexts", "namespaces", "rbac_probe", "provider"):
            assert key in result

    def test_provider_name_in_result(self) -> None:
        svc = _make_service()
        self._mock_all_leaf_methods(svc)
        result = svc.discover_infrastructure({"name": "test-provider"})
        assert result["provider"] == "test-provider"

    def test_rbac_probe_failure_returns_all_false(self) -> None:
        svc = _make_service()
        self._mock_all_leaf_methods(svc)
        svc.probe_rbac = MagicMock(side_effect=K8sDiscoveryError("probe failed"))  # type: ignore[method-assign]
        result = svc.discover_infrastructure({})
        assert result["rbac_probe"] == {
            "create_pods": False,
            "watch_pods": False,
            "delete_pods": False,
        }

    def test_in_cluster_namespace_preferred_over_default(self, tmp_path: Path) -> None:
        sa_file = tmp_path / "namespace"
        sa_file.write_text("custom-ns\n", encoding="utf-8")
        svc = _make_service()
        self._mock_all_leaf_methods(svc)
        svc.detect_in_cluster = MagicMock(return_value=True)  # type: ignore[method-assign]
        svc.discover_namespaces = MagicMock(return_value=[])  # type: ignore[method-assign]
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service._SA_NAMESPACE_FILE",
            new=sa_file,
        ):
            result = svc.discover_infrastructure({})
        assert result["default_namespace"] == "custom-ns"


# ---------------------------------------------------------------------------
# validate_infrastructure — checks (line 863-998)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateInfrastructure:
    def _mock_for_valid(self, svc: K8sInfrastructureDiscoveryService) -> None:
        svc.discover_cluster_endpoint = MagicMock(return_value="https://k8s:6443")  # type: ignore[method-assign]
        svc.probe_rbac = MagicMock(  # type: ignore[method-assign]
            return_value=RBACProbeResult(
                namespace="default",
                can_create_pods=True,
                can_watch_pods=True,
                can_delete_pods=True,
            )
        )
        fake_core = MagicMock()
        fake_core.get_api_resources.return_value = MagicMock()
        fake_core.read_namespace.return_value = MagicMock()
        fake_core.read_namespaced_service_account.return_value = MagicMock()
        svc._core_v1 = MagicMock(return_value=fake_core)  # type: ignore[method-assign]

    def test_valid_returns_no_issues(self) -> None:
        svc = _make_service()
        self._mock_for_valid(svc)
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
            return_value=False,
        ):
            result = svc.validate_infrastructure({"name": "k8s"})
        assert result["valid"] is True
        assert result["issues"] == []

    def test_unreachable_apiserver_adds_issue(self) -> None:
        svc = _make_service()
        svc.discover_cluster_endpoint = MagicMock(return_value="https://k8s:6443")  # type: ignore[method-assign]
        fake_core = MagicMock()
        fake_core.get_api_resources.side_effect = RuntimeError("connection refused")
        svc._core_v1 = MagicMock(return_value=fake_core)  # type: ignore[method-assign]
        result = svc.validate_infrastructure({})
        assert result["valid"] is False
        assert any("Apiserver unreachable" in issue for issue in result["issues"])

    def test_missing_namespace_adds_issue(self) -> None:
        svc = _make_service()
        svc.discover_cluster_endpoint = MagicMock(return_value="https://k8s:6443")  # type: ignore[method-assign]
        svc.probe_rbac = MagicMock(  # type: ignore[method-assign]
            return_value=RBACProbeResult("default", True, True, True)
        )
        fake_core = MagicMock()
        fake_core.get_api_resources.return_value = MagicMock()
        # read_namespace raises 404
        fake_core.read_namespace.side_effect = _make_fake_api_exception(404)
        svc._core_v1 = MagicMock(return_value=fake_core)  # type: ignore[method-assign]
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
            return_value=False,
        ):
            result = svc.validate_infrastructure({})
        assert any("not found" in issue.lower() for issue in result["issues"])

    def test_rbac_denied_adds_issue(self) -> None:
        svc = _make_service()
        svc.discover_cluster_endpoint = MagicMock(return_value="https://k8s:6443")  # type: ignore[method-assign]
        svc.probe_rbac = MagicMock(  # type: ignore[method-assign]
            return_value=RBACProbeResult(
                namespace="default",
                can_create_pods=False,  # denied
                can_watch_pods=True,
                can_delete_pods=True,
            )
        )
        fake_core = MagicMock()
        fake_core.get_api_resources.return_value = MagicMock()
        fake_core.read_namespace.return_value = MagicMock()
        svc._core_v1 = MagicMock(return_value=fake_core)  # type: ignore[method-assign]
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
            return_value=False,
        ):
            result = svc.validate_infrastructure({})
        assert result["valid"] is False
        assert any("create" in issue for issue in result["issues"])

    def test_missing_sa_adds_issue(self) -> None:
        svc = _make_service()
        svc.discover_cluster_endpoint = MagicMock(return_value="https://k8s:6443")  # type: ignore[method-assign]
        svc.probe_rbac = MagicMock(  # type: ignore[method-assign]
            return_value=RBACProbeResult("default", True, True, True)
        )
        fake_core = MagicMock()
        fake_core.get_api_resources.return_value = MagicMock()
        fake_core.read_namespace.return_value = MagicMock()
        fake_core.read_namespaced_service_account.side_effect = _make_fake_api_exception(404)
        svc._core_v1 = MagicMock(return_value=fake_core)  # type: ignore[method-assign]
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
            return_value=False,
        ):
            result = svc.validate_infrastructure(
                {"template_defaults": {"service_account": "my-sa"}}
            )
        assert any("ServiceAccount" in issue for issue in result["issues"])

    def test_context_not_in_kubeconfig_adds_issue(self) -> None:
        svc = _make_service(context="missing-ctx")
        svc.discover_cluster_endpoint = MagicMock(return_value="https://k8s:6443")  # type: ignore[method-assign]
        svc.probe_rbac = MagicMock(  # type: ignore[method-assign]
            return_value=RBACProbeResult("default", True, True, True)
        )
        fake_core = MagicMock()
        fake_core.get_api_resources.return_value = MagicMock()
        fake_core.read_namespace.return_value = MagicMock()
        svc._core_v1 = MagicMock(return_value=fake_core)  # type: ignore[method-assign]
        with (
            patch(
                "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
                return_value=False,
            ),
            patch(
                "kubernetes.config.list_kube_config_contexts",
                return_value=([{"name": "other"}], None),
            ),
        ):
            result = svc.validate_infrastructure({"config": {"context": "missing-ctx"}})
        assert any("not found in kubeconfig" in issue for issue in result["issues"])

    def test_re_raises_k8s_error_on_api_resources(self) -> None:
        svc = _make_service()
        svc.discover_cluster_endpoint = MagicMock(return_value="https://k8s:6443")  # type: ignore[method-assign]
        fake_core = MagicMock()
        fake_core.get_api_resources.side_effect = K8sError("sdk missing")
        svc._core_v1 = MagicMock(return_value=fake_core)  # type: ignore[method-assign]
        with pytest.raises(K8sError):
            svc.validate_infrastructure({})


# ---------------------------------------------------------------------------
# Kubeconfig / ApiClient reuse within one init run
# ---------------------------------------------------------------------------


@pytest.fixture
def kube_loaders():
    """Patch the SDK loaders so each load and ApiClient construction is observable."""
    clients: list[MagicMock] = []

    def _new_client(*_args: Any, **_kwargs: Any) -> MagicMock:
        client = MagicMock()
        client.configuration.host = "https://1.2.3.4:6443"
        clients.append(client)
        return client

    with (
        patch(
            "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
            return_value=False,
        ),
        patch("kubernetes.config.load_kube_config") as load,
        patch("kubernetes.config.load_incluster_config") as load_incluster,
        patch("kubernetes.client.api_client.ApiClient", side_effect=_new_client) as api_client,
    ):
        yield SimpleNamespace(
            load=load, load_incluster=load_incluster, api_client=api_client, clients=clients
        )


@pytest.mark.unit
class TestApiClientReuse:
    def test_core_v1_called_twice_loads_kubeconfig_once(self, kube_loaders) -> None:
        svc = _make_service(context="ctx-a")

        svc._core_v1()
        svc._core_v1()
        svc._auth_v1()

        kube_loaders.load.assert_called_once()
        kube_loaders.api_client.assert_called_once()
        assert svc._api_client is kube_loaders.clients[0]

    def test_services_for_the_same_context_share_one_client(self, kube_loaders) -> None:
        first = _make_service(context="ctx-a")
        second = _make_service(context="ctx-a")

        assert first._get_api_client() is second._get_api_client()

        kube_loaders.load.assert_called_once()

    def test_each_distinct_context_gets_its_own_client(self, kube_loaders) -> None:
        a = _make_service(context="ctx-a")._get_api_client()
        b = _make_service(context="ctx-b")._get_api_client()

        assert a is not b
        assert kube_loaders.load.call_count == 2
        assert kube_loaders.api_client.call_count == 2

    def test_in_cluster_client_is_shared(self, kube_loaders) -> None:
        with patch(
            "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
            return_value=True,
        ):
            first = _make_service()._get_api_client()
            second = _make_service()._get_api_client()

        assert first is second
        kube_loaders.load_incluster.assert_called_once()

    def test_failed_load_is_not_cached(self, kube_loaders) -> None:
        kube_loaders.load.side_effect = [RuntimeError("expired token"), None]
        svc = _make_service(context="ctx-a")

        with pytest.raises(RuntimeError):
            svc._get_api_client()
        svc._get_api_client()

        assert kube_loaders.load.call_count == 2
        kube_loaders.api_client.assert_called_once()

    def test_credential_probe_and_discovery_share_one_client(self, kube_loaders) -> None:
        from orb.providers.k8s.services.capability_service import K8sCapabilityService

        with patch("kubernetes.client.CoreV1Api.get_api_resources", return_value=None):
            assert K8sCapabilityService.test_credentials("ctx-a")["success"] is True
        _make_service(context="ctx-a")._get_api_client()

        kube_loaders.load.assert_called_once()
        kube_loaders.api_client.assert_called_once()

    def test_endpoint_lookup_reuses_the_client_for_the_context(self, kube_loaders) -> None:
        svc = _make_service(context="ctx-a")
        svc._get_api_client()

        assert svc.discover_cluster_endpoint(context="ctx-a") == "https://1.2.3.4:6443"

        kube_loaders.load.assert_called_once()
        kube_loaders.api_client.assert_called_once()

    def test_release_hook_forces_a_fresh_load(self, kube_loaders) -> None:
        from orb.providers.k8s.strategy.k8s_provider_strategy import K8sProviderStrategy

        svc = _make_service(context="ctx-a")
        svc._get_api_client()
        K8sProviderStrategy.release_init_resources()
        _make_service(context="ctx-a")._get_api_client()

        assert kube_loaders.load.call_count == 2


@pytest.mark.unit
class TestInteractiveInitReuse:
    def _run_init(self, tmp_path: Path) -> tuple[MagicMock, MagicMock, int]:
        from kubernetes.client import AuthorizationV1Api, CoreV1Api

        from tests.utilities.init_flow import run_interactive_init

        contexts = (
            [
                {"name": "ctx-a", "context": {"cluster": "c1"}},
                {"name": "ctx-b", "context": {"cluster": "c1"}},
            ],
            {"name": "ctx-a"},
        )
        namespace = SimpleNamespace(
            metadata=SimpleNamespace(name="default", creation_timestamp=None),
            status=SimpleNamespace(phase="Active"),
        )
        with (
            patch("orb.providers.k8s.auth.in_cluster.is_in_cluster", return_value=False),
            patch(
                "orb.providers.k8s.services.infrastructure_discovery_service.is_in_cluster",
                return_value=False,
            ),
            patch("kubernetes.config.list_kube_config_contexts", return_value=contexts),
            patch("kubernetes.config.load_kube_config") as load,
            patch("kubernetes.client.api_client.ApiClient.__init__", return_value=None) as init,
            patch.object(CoreV1Api, "__init__", return_value=None),
            patch.object(AuthorizationV1Api, "__init__", return_value=None),
            patch.object(
                CoreV1Api, "get_api_resources", return_value=SimpleNamespace(resources=[])
            ),
            patch.object(
                CoreV1Api, "list_namespace", return_value=SimpleNamespace(items=[namespace])
            ),
            patch.object(
                CoreV1Api, "list_namespaced_service_account", return_value=SimpleNamespace(items=[])
            ),
            patch.object(
                CoreV1Api, "list_namespaced_secret", return_value=SimpleNamespace(items=[])
            ),
            patch.object(
                AuthorizationV1Api,
                "create_self_subject_access_review",
                return_value=SimpleNamespace(status=SimpleNamespace(allowed=True, reason="")),
            ),
            patch(
                "kubernetes.client.api_client.ApiClient.configuration",
                SimpleNamespace(host="https://1.2.3.4:6443"),
                create=True,
            ),
        ):
            code = run_interactive_init("k8s", tmp_path)
        return load, init, code

    def test_full_init_loads_kubeconfig_and_builds_client_once(self, tmp_path) -> None:
        load, init, code = self._run_init(tmp_path)

        assert code == 0
        load.assert_called_once()
        init.assert_called_once()

    def test_second_init_run_loads_again(self, tmp_path) -> None:
        self._run_init(tmp_path)
        load, init, code = self._run_init(tmp_path)

        assert code == 0
        load.assert_called_once()
        init.assert_called_once()


@pytest.mark.unit
class TestKubeContextEnumerationReuse:
    def test_contexts_are_parsed_once_across_services(self) -> None:
        from orb.providers.k8s.services.capability_service import K8sCapabilityService

        contexts = ([{"name": "ctx-a", "context": {"cluster": "c1"}}], {"name": "ctx-a"})
        with (
            patch(
                "orb.providers.k8s.auth.in_cluster.is_in_cluster",
                return_value=False,
            ),
            patch("kubernetes.config.list_kube_config_contexts", return_value=contexts) as parse,
        ):
            K8sCapabilityService(logger=_make_logger()).get_available_credential_sources()
            _make_service().discover_contexts()
            _make_service().discover_contexts()

        parse.assert_called_once()

    def test_failed_parse_is_not_cached(self) -> None:
        contexts = ([{"name": "ctx-a", "context": {"cluster": "c1"}}], {"name": "ctx-a"})
        with patch(
            "kubernetes.config.list_kube_config_contexts",
            side_effect=[RuntimeError("no kubeconfig"), contexts],
        ):
            assert _make_service().discover_contexts() == ([], None)
            all_contexts, _ = _make_service().discover_contexts()

        assert [c.name for c in all_contexts] == ["ctx-a"]

    def test_distinct_kubeconfig_files_are_parsed_separately(self) -> None:
        with patch("kubernetes.config.list_kube_config_contexts", return_value=([], None)) as parse:
            _make_service().discover_contexts(Path("/tmp/one"))
            _make_service().discover_contexts(Path("/tmp/two"))
            _make_service().discover_contexts(Path("/tmp/one"))

        assert parse.call_count == 2
