"""Focused tests for Azure credential factory helpers."""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orb.providers.azure.infrastructure.credential_factory import (
    AsyncAzureCredentialAccessTokenProvider,
    AsyncDefaultAzureAccessTokenProvider,
    AzureCredentialAccessTokenProvider,
    DefaultAzureAccessTokenProvider,
    create_default_azure_credential,
    create_default_azure_credential_async,
    get_default_azure_credential_error_types,
)


def test_azure_credential_access_token_provider_adapts_existing_credential():
    credential = MagicMock()
    credential.get_token.return_value = types.SimpleNamespace(token="access-token")

    provider = AzureCredentialAccessTokenProvider(credential)

    assert provider.get_access_token("scope") == "access-token"
    credential.get_token.assert_called_once_with("scope")


def test_create_default_azure_credential_passes_managed_identity_client_id_when_configured():
    fake_identity = types.ModuleType("azure.identity")
    fake_ctor = MagicMock(return_value=MagicMock())
    fake_identity.DefaultAzureCredential = fake_ctor
    logger = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "azure": types.ModuleType("azure"),
            "azure.identity": fake_identity,
        },
    ):
        credential = create_default_azure_credential(
            client_id="managed-identity-client-id",
            logger=logger,
        )

    assert credential is fake_ctor.return_value
    fake_ctor.assert_called_once_with(managed_identity_client_id="managed-identity-client-id")
    logger.debug.assert_called_once_with("Azure DefaultAzureCredential initialised")
    logger.info.assert_not_called()


def test_create_default_azure_credential_omits_managed_identity_client_id_when_unset():
    fake_identity = types.ModuleType("azure.identity")
    fake_ctor = MagicMock(return_value=MagicMock())
    fake_identity.DefaultAzureCredential = fake_ctor

    with patch.dict(
        sys.modules,
        {
            "azure": types.ModuleType("azure"),
            "azure.identity": fake_identity,
        },
    ):
        create_default_azure_credential(
            client_id=None,
            logger=MagicMock(),
        )

    fake_ctor.assert_called_once_with()


def test_create_default_azure_credential_async_preserves_nested_import_error():
    fake_identity_aio = types.ModuleType("azure.identity.aio")
    fake_ctor = MagicMock(side_effect=ImportError("aiohttp package is not installed"))
    fake_identity_aio.DefaultAzureCredential = fake_ctor
    logger = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "azure": types.ModuleType("azure"),
            "azure.identity": types.ModuleType("azure.identity"),
            "azure.identity.aio": fake_identity_aio,
        },
    ):
        with pytest.raises(ImportError, match="aiohttp package is not installed"):
            create_default_azure_credential_async(
                client_id=None,
                logger=logger,
            )

    logger.error.assert_called_once_with(
        "azure-identity dependency error: aiohttp package is not installed"
    )


@pytest.mark.asyncio
async def test_async_azure_credential_access_token_provider_adapts_existing_credential():
    credential = MagicMock()
    credential.get_token = AsyncMock(return_value=types.SimpleNamespace(token="access-token"))

    provider = AsyncAzureCredentialAccessTokenProvider(credential)

    assert await provider.get_access_token("scope") == "access-token"
    credential.get_token.assert_awaited_once_with("scope")


def test_create_default_azure_credential_async_passes_managed_identity_client_id_when_configured():
    fake_identity_aio = types.ModuleType("azure.identity.aio")
    fake_ctor = MagicMock(return_value=MagicMock())
    fake_identity_aio.DefaultAzureCredential = fake_ctor
    logger = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "azure": types.ModuleType("azure"),
            "azure.identity": types.ModuleType("azure.identity"),
            "azure.identity.aio": fake_identity_aio,
        },
    ):
        credential = create_default_azure_credential_async(
            client_id="managed-identity-client-id",
            logger=logger,
        )

    assert credential is fake_ctor.return_value
    fake_ctor.assert_called_once_with(managed_identity_client_id="managed-identity-client-id")
    logger.debug.assert_called_once_with("Async Azure DefaultAzureCredential initialised")
    logger.info.assert_not_called()


def test_default_azure_access_token_provider_closes_short_lived_credential():
    fake_identity = types.ModuleType("azure.identity")
    fake_credential = MagicMock()
    fake_credential.get_token.return_value = types.SimpleNamespace(token="access-token")
    fake_ctor = MagicMock(return_value=fake_credential)
    fake_identity.DefaultAzureCredential = fake_ctor

    with patch.dict(
        sys.modules,
        {
            "azure": types.ModuleType("azure"),
            "azure.identity": fake_identity,
        },
    ):
        provider = DefaultAzureAccessTokenProvider(
            logger=MagicMock(),
            client_id=None,
        )
        token = provider.get_access_token("https://management.azure.com/.default")

    assert token == "access-token"
    fake_credential.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_async_default_azure_access_token_provider_closes_short_lived_credential():
    fake_identity_aio = types.ModuleType("azure.identity.aio")
    fake_credential = MagicMock()
    fake_credential.get_token = AsyncMock(return_value=types.SimpleNamespace(token="access-token"))
    fake_credential.close = AsyncMock()
    fake_ctor = MagicMock(return_value=fake_credential)
    fake_identity_aio.DefaultAzureCredential = fake_ctor

    with patch.dict(
        sys.modules,
        {
            "azure": types.ModuleType("azure"),
            "azure.identity": types.ModuleType("azure.identity"),
            "azure.identity.aio": fake_identity_aio,
        },
    ):
        provider = AsyncDefaultAzureAccessTokenProvider(
            logger=MagicMock(),
            client_id=None,
        )
        token = await provider.get_access_token("https://management.azure.com/.default")

    assert token == "access-token"
    fake_credential.close.assert_awaited_once_with()


def test_get_default_azure_credential_error_types_returns_sdk_types_when_available():
    fake_core = types.ModuleType("azure.core.exceptions")
    fake_identity = types.ModuleType("azure.identity")

    class FakeClientAuthenticationError(Exception):
        pass

    class FakeCredentialUnavailableError(Exception):
        pass

    fake_core.ClientAuthenticationError = FakeClientAuthenticationError
    fake_identity.CredentialUnavailableError = FakeCredentialUnavailableError

    with patch.dict(
        sys.modules,
        {
            "azure": types.ModuleType("azure"),
            "azure.core": types.ModuleType("azure.core"),
            "azure.core.exceptions": fake_core,
            "azure.identity": fake_identity,
        },
    ):
        assert get_default_azure_credential_error_types() == (
            FakeCredentialUnavailableError,
            FakeClientAuthenticationError,
        )


def test_default_azure_access_token_provider_reports_import_error_as_expected_auth_type():
    provider = DefaultAzureAccessTokenProvider(
        logger=MagicMock(),
        client_id=None,
    )

    assert ImportError in provider.get_auth_error_types()


# ---------------------------------------------------------------------------
# Shared (init-scoped) credentials
# ---------------------------------------------------------------------------

_FACTORY = "orb.providers.azure.infrastructure.credential_factory.create_default_azure_credential"


def test_shared_credential_is_created_once_per_client_id():
    from orb.providers.azure.infrastructure.credential_factory import (
        get_shared_default_azure_credential,
    )

    with patch(_FACTORY, side_effect=lambda **_: MagicMock()) as create:
        first = get_shared_default_azure_credential(None)
        again = get_shared_default_azure_credential(None)
        other = get_shared_default_azure_credential("identity-id")

    assert first is again
    assert other is not first
    assert create.call_count == 2
    assert [call.kwargs["client_id"] for call in create.call_args_list] == [None, "identity-id"]


def test_failed_shared_credential_creation_is_not_cached():
    from orb.providers.azure.infrastructure.credential_factory import (
        get_shared_default_azure_credential,
    )

    credential = MagicMock()
    with patch(_FACTORY, side_effect=[ImportError("azure-identity"), credential]):
        with pytest.raises(ImportError):
            get_shared_default_azure_credential(None)
        assert get_shared_default_azure_credential(None) is credential


def test_close_shared_credentials_closes_each_once_and_forgets_them():
    from orb.providers.azure.infrastructure.credential_factory import (
        close_shared_credentials,
        get_shared_default_azure_credential,
    )

    credentials = [MagicMock(), MagicMock()]
    with patch(_FACTORY, side_effect=credentials) as create:
        get_shared_default_azure_credential(None)
        get_shared_default_azure_credential("identity-id")
        get_shared_default_azure_credential(None)
        close_shared_credentials()
        close_shared_credentials()

    for credential in credentials:
        credential.close.assert_called_once_with()
    with patch(_FACTORY, return_value=MagicMock()) as recreate:
        get_shared_default_azure_credential(None)
    assert create.call_count == 2
    recreate.assert_called_once()


def test_close_shared_credentials_survives_a_failing_close():
    from orb.providers.azure.infrastructure.credential_factory import (
        close_shared_credentials,
        get_shared_default_azure_credential,
    )

    broken, healthy = MagicMock(), MagicMock()
    broken.close.side_effect = RuntimeError("transport gone")
    with patch(_FACTORY, side_effect=[broken, healthy]):
        get_shared_default_azure_credential(None)
        get_shared_default_azure_credential("identity-id")
        close_shared_credentials()

    healthy.close.assert_called_once_with()


def test_suppress_azure_identity_warnings_restores_the_previous_level():
    import logging

    from orb.providers.azure.infrastructure.credential_factory import (
        suppress_azure_identity_warnings,
    )

    def _fail() -> None:
        raise RuntimeError("boom")

    identity_logger = logging.getLogger("azure.identity")
    chain_logger = logging.getLogger("azure.identity._credentials.chained")
    previous = identity_logger.level
    identity_logger.setLevel(logging.INFO)
    try:
        with suppress_azure_identity_warnings():
            assert not chain_logger.isEnabledFor(logging.WARNING)
            assert chain_logger.isEnabledFor(logging.ERROR)
        assert identity_logger.level == logging.INFO

        with pytest.raises(RuntimeError):
            with suppress_azure_identity_warnings():
                _fail()
        assert identity_logger.level == logging.INFO
    finally:
        identity_logger.setLevel(previous)


def test_overlapping_suppression_blocks_restore_the_level_once_all_have_exited():
    import logging
    import threading

    from orb.providers.azure.infrastructure.credential_factory import (
        suppress_azure_identity_warnings,
    )

    identity_logger = logging.getLogger("azure.identity")
    previous = identity_logger.level
    identity_logger.setLevel(logging.INFO)
    first_inside, second_inside, release_second = (threading.Event() for _ in range(3))

    def first():
        with suppress_azure_identity_warnings():
            first_inside.set()
            second_inside.wait(timeout=5)

    def second():
        first_inside.wait(timeout=5)
        with suppress_azure_identity_warnings():
            second_inside.set()
            release_second.wait(timeout=5)

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    try:
        for thread in threads:
            thread.start()
        threads[0].join(timeout=5)
        assert identity_logger.level == logging.ERROR
        release_second.set()
        threads[1].join(timeout=5)
        assert identity_logger.level == logging.INFO
    finally:
        release_second.set()
        identity_logger.setLevel(previous)


# ---------------------------------------------------------------------------
# A shared credential keeps issuing valid tokens after they expire
# ---------------------------------------------------------------------------

_TOKEN_LIFETIME_SECONDS = 3600
_SCOPE = "https://management.azure.com/.default"


class _Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


class _ExpiringCredential:
    """Fake credential that, like the SDK's, caches a token and re-mints once it lapses."""

    def __init__(self, clock: _Clock) -> None:
        self._clock = clock
        self._token = None
        self.minted = 0

    def get_token(self, *scopes, **kwargs):
        from azure.core.credentials import AccessToken

        if self._token is None or self._token.expires_on <= self._clock():
            self.minted += 1
            self._token = AccessToken(
                f"t{self.minted}", int(self._clock()) + _TOKEN_LIFETIME_SECONDS
            )
        return self._token

    def close(self) -> None:
        pass


@pytest.fixture
def expiring_default_credential(monkeypatch):
    """Replace ``DefaultAzureCredential`` with a credential driven by a fake clock."""
    import azure.identity

    clock = _Clock()
    constructor = MagicMock(side_effect=lambda **_: _ExpiringCredential(clock))
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", constructor)
    return clock, constructor


def test_shared_credential_issues_a_new_token_after_the_first_expires(expiring_default_credential):
    from orb.providers.azure.infrastructure.credential_factory import (
        get_shared_default_azure_credential,
    )

    clock, constructor = expiring_default_credential
    credential = get_shared_default_azure_credential(None)
    provider = AzureCredentialAccessTokenProvider(credential)

    before = provider.get_access_token(_SCOPE)
    assert provider.get_access_token(_SCOPE) == before
    clock.now += 2 * _TOKEN_LIFETIME_SECONDS
    after = provider.get_access_token(_SCOPE)

    assert (before, after) == ("t1", "t2")
    assert get_shared_default_azure_credential(None) is credential
    constructor.assert_called_once_with()
    assert credential.minted == 2


def test_management_pipeline_on_a_shared_credential_sends_the_refreshed_token(
    expiring_default_credential, monkeypatch
):
    """The SDK's bearer policy, as used by the discovery clients, re-requests an expired token."""
    from azure.core.pipeline import PipelineContext, PipelineRequest
    from azure.core.pipeline.policies import BearerTokenCredentialPolicy, _authentication
    from azure.core.rest import HttpRequest

    from orb.providers.azure.infrastructure.credential_factory import (
        get_shared_default_azure_credential,
    )

    clock, _ = expiring_default_credential
    monkeypatch.setattr(_authentication, "time", types.SimpleNamespace(time=clock))
    credential = get_shared_default_azure_credential(None)
    policy = BearerTokenCredentialPolicy(credential, _SCOPE)

    def authorization() -> str:
        request = PipelineRequest(
            HttpRequest("GET", "https://management.azure.com/"), PipelineContext(None)
        )
        policy.on_request(request)
        return request.http_request.headers["Authorization"]

    first = authorization()
    assert authorization() == first
    clock.now += 2 * _TOKEN_LIFETIME_SECONDS

    assert (first, authorization()) == ("Bearer t1", "Bearer t2")
    assert credential.minted == 2
