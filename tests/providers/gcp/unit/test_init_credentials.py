"""GCP init validates Application Default Credentials before provider construction."""

import base64
import json
from unittest.mock import MagicMock
from urllib.parse import parse_qs

import google.auth
import google.auth.credentials
import google.auth.transport.requests
from google.oauth2 import service_account

from orb.providers.gcp.services.health_check_service import GCPHealthCheckService


def test_authentication_refreshes_adc(monkeypatch) -> None:
    credentials = MagicMock()
    auth_default = MagicMock(return_value=(credentials, "selected-project"))
    monkeypatch.setattr(google.auth, "default", auth_default)

    assert GCPHealthCheckService.authenticate() == "selected-project"
    auth_default.assert_called_once_with(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh.assert_called_once()


def test_service_account_adc_refresh_includes_cloud_platform_scope(monkeypatch) -> None:
    signer = MagicMock()
    signer.key_id = "test-key"
    signer.sign.return_value = b"test-signature"
    request_payloads = []

    def default_credentials(*, scopes):
        credentials = service_account.Credentials(
            signer=signer,
            service_account_email="test@example.iam.gserviceaccount.com",
            token_uri="https://oauth2.googleapis.com/token",
            scopes=scopes,
        )
        return credentials, "test-project"

    def token_request(**kwargs):
        request_payloads.append(kwargs["body"])
        return MagicMock(
            status=200,
            data=json.dumps(
                {"access_token": "test-token", "expires_in": 3600, "token_type": "Bearer"}
            ).encode(),
        )

    monkeypatch.setattr(google.auth, "default", default_credentials)
    monkeypatch.setattr(google.auth.transport.requests, "Request", lambda: token_request)

    assert GCPHealthCheckService.authenticate() == "test-project"
    assertion = parse_qs(request_payloads[0].decode())["assertion"][0]
    encoded_claims = assertion.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(encoded_claims + "=="))
    assert claims["scope"] == "https://www.googleapis.com/auth/cloud-platform"


def test_init_credential_check_refreshes_cached_adc(monkeypatch) -> None:
    credentials = MagicMock()
    auth_default = MagicMock(return_value=(credentials, "selected-project"))
    monkeypatch.setattr(google.auth, "default", auth_default)

    first = GCPHealthCheckService.test_credentials("adc")
    second = GCPHealthCheckService.test_credentials("adc")

    assert first == second == {"success": True, "project_id": "selected-project"}
    auth_default.assert_called_once()
    assert credentials.refresh.call_count == 2


def test_failed_credential_check_is_not_cached_so_a_retry_resolves_again(monkeypatch) -> None:
    stale, fresh = MagicMock(), MagicMock()
    stale.refresh.side_effect = RuntimeError("invalid_grant")
    auth_default = MagicMock(side_effect=[(stale, "project"), (fresh, "project")])
    monkeypatch.setattr(google.auth, "default", auth_default)

    first = GCPHealthCheckService.test_credentials("adc")
    second = GCPHealthCheckService.test_credentials("adc")

    assert first["success"] is False
    assert second == {"success": True, "project_id": "project"}
    assert auth_default.call_count == 2


def test_runtime_health_check_does_not_use_init_cached_adc(monkeypatch) -> None:
    from orb.providers.gcp.services import init_discovery

    init_credentials = MagicMock()
    runtime_credentials = MagicMock()
    auth_default = MagicMock(
        side_effect=[(init_credentials, "project"), (runtime_credentials, "project")]
    )
    monkeypatch.setattr(google.auth, "default", auth_default)

    init_discovery.default_project()
    assert GCPHealthCheckService.authenticate() == "project"

    assert auth_default.call_count == 2
    init_credentials.refresh.assert_not_called()
    runtime_credentials.refresh.assert_called_once()


def test_init_credential_check_hints_at_the_gcp_extra_when_sdk_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "orb.providers.gcp.services.init_discovery.cached_default_credentials",
        MagicMock(side_effect=ImportError("No module named 'google'")),
    )

    assert GCPHealthCheckService.test_credentials("adc") == {
        "success": False,
        "error": "Install orb-py[gcp] to use GCP init.",
    }


def test_init_credential_check_reports_other_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        "orb.providers.gcp.services.init_discovery.cached_default_credentials",
        MagicMock(side_effect=RuntimeError("ADC unavailable")),
    )

    assert GCPHealthCheckService.test_credentials("adc") == {
        "success": False,
        "error": "GCP credential check failed: ADC unavailable",
    }


def _stub_gcp_sdk(monkeypatch) -> MagicMock:
    credentials = MagicMock()
    auth_default = MagicMock(return_value=(credentials, "example-project"))
    monkeypatch.setattr(google.auth, "default", auth_default)
    session = MagicMock()

    def get(url, **_kwargs):
        response = MagicMock()
        if "projects:search" in url:
            response.json.return_value = {
                "projects": [
                    {"projectId": "example-project", "displayName": "Example", "state": "ACTIVE"}
                ]
            }
        else:
            response.json.return_value = {"items": [{"name": "us-central1", "status": "UP"}]}
        return response

    session.get.side_effect = get
    monkeypatch.setattr(
        google.auth.transport.requests, "AuthorizedSession", MagicMock(return_value=session)
    )
    return auth_default


def test_full_init_resolves_adc_once(monkeypatch, tmp_path) -> None:
    from tests.utilities.init_flow import run_interactive_init

    auth_default = _stub_gcp_sdk(monkeypatch)

    assert run_interactive_init("gcp", tmp_path) == 0

    auth_default.assert_called_once()


def test_second_init_run_resolves_adc_again(monkeypatch, tmp_path) -> None:
    from tests.utilities.init_flow import run_interactive_init

    auth_default = _stub_gcp_sdk(monkeypatch)

    run_interactive_init("gcp", tmp_path)
    run_interactive_init("gcp", tmp_path)

    assert auth_default.call_count == 2


class _ExpiringCredentials(google.auth.credentials.Credentials):
    """ADC stand-in whose validity follows a fake clock and whose refresh mints a new token."""

    LIFETIME_SECONDS = 3600

    def __init__(self) -> None:
        super().__init__()
        self.now = 1_000_000.0
        self.refreshes = 0

    @property
    def expired(self) -> bool:
        return self.expiry is not None and self.now >= self.expiry

    def refresh(self, request) -> None:
        self.refreshes += 1
        self.token = f"token-{self.refreshes}"
        self.expiry = self.now + self.LIFETIME_SECONDS


def _stub_transport(monkeypatch) -> list[str]:
    """Answer every HTTPS request locally and return the Authorization header of each."""
    import requests

    sent: list[str] = []

    def send(self, request, **_kwargs):
        sent.append(request.headers.get("Authorization", ""))
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"projects": []}).encode()
        response.request = request
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return sent


def test_cached_adc_refreshes_and_sends_the_new_token_after_expiry(monkeypatch) -> None:
    from orb.providers.gcp.services import init_discovery

    credentials = _ExpiringCredentials()
    auth_default = MagicMock(return_value=(credentials, "example-project"))
    monkeypatch.setattr(google.auth, "default", auth_default)
    sent = _stub_transport(monkeypatch)

    init_discovery.list_projects()
    init_discovery.list_projects()
    credentials.now += 2 * _ExpiringCredentials.LIFETIME_SECONDS
    init_discovery.list_projects()

    assert sent == ["Bearer token-1", "Bearer token-1", "Bearer token-2"]
    assert credentials.refreshes == 2
    auth_default.assert_called_once()
    assert init_discovery.cached_default_credentials()[0] is credentials


def test_cli_init_writes_gcp_config_and_resolves_adc_once(monkeypatch, tmp_path) -> None:
    from tests.utilities.init_flow import run_cli_init

    auth_default = _stub_gcp_sdk(monkeypatch)

    code, config = run_cli_init("gcp", tmp_path)

    assert code == 0
    (provider,) = config["provider"]["providers"]
    assert provider["type"] == "gcp"
    assert provider["config"] == {"project_id": "example-project", "region": "us-central1"}
    assert config["provider"]["default_provider_instance"] == provider["name"]
    auth_default.assert_called_once()
