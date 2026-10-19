"""Azure credential construction owned by Azure infrastructure."""

from __future__ import annotations

import contextlib
import logging
import threading
from collections.abc import Iterator
from typing import Any, Optional, Protocol

from orb.domain.base.ports import LoggingPort


class AzureCredentialProtocol(Protocol):
    """Credential surface required by Azure provider code."""

    def get_token(self, *scopes: str, **kwargs: Any) -> Any:
        """Request an access token for the given scopes."""
        pass

    def close(self) -> None:
        """Release any resources held by this credential."""
        pass


class AsyncAzureCredentialProtocol(Protocol):
    """Async credential surface required by native async Azure SDK flows."""

    async def get_token(self, *scopes: str, **kwargs: Any) -> Any:
        """Asynchronously request an access token for the given scopes."""
        pass

    async def close(self) -> None:
        """Release any resources held by this async credential."""
        pass


class AzureAccessTokenProviderProtocol(Protocol):
    """Short-lived Azure token provider used by auth flows."""

    def get_access_token(self, scope: str) -> str:  # type: ignore[return]
        """Return a raw access-token string for the given scope."""
        pass

    def get_auth_error_types(self) -> tuple[type[Exception], ...]:  # type: ignore[return]
        """Return exception types that signal authentication failures."""
        pass


class AsyncAzureAccessTokenProviderProtocol(Protocol):
    """Async short-lived Azure token provider used by native async auth flows."""

    async def get_access_token(self, scope: str) -> str:  # type: ignore[return]
        """Return a raw access-token string for the given scope."""
        pass

    def get_auth_error_types(self) -> tuple[type[Exception], ...]:  # type: ignore[return]
        """Return exception types that signal authentication failures."""
        pass


class AzureCredentialAccessTokenProvider(AzureAccessTokenProviderProtocol):
    """Adapt an existing Azure credential to the token-provider protocol."""

    def __init__(self, credential: AzureCredentialProtocol) -> None:
        self._credential = credential

    def get_access_token(self, scope: str) -> str:
        """Delegate token retrieval to the wrapped credential."""
        token = self._credential.get_token(scope)
        return token.token

    def get_auth_error_types(self) -> tuple[type[Exception], ...]:
        """Return Azure SDK credential error types."""
        return get_default_azure_credential_error_types()


class AsyncAzureCredentialAccessTokenProvider(AsyncAzureAccessTokenProviderProtocol):
    """Adapt an async Azure credential to the async token-provider protocol."""

    def __init__(self, credential: AsyncAzureCredentialProtocol) -> None:
        self._credential = credential

    async def get_access_token(self, scope: str) -> str:
        """Delegate token retrieval to the wrapped async credential."""
        token = await self._credential.get_token(scope)
        return token.token

    def get_auth_error_types(self) -> tuple[type[Exception], ...]:
        """Return Azure SDK credential error types."""
        return get_default_azure_credential_error_types()


def format_import_error(package_name: str, exc: ImportError) -> str:
    """Return a precise dependency error message without masking nested imports."""
    message = str(exc).strip()
    if not message:
        return f"{package_name} package is not installed"
    return f"{package_name} dependency error: {message}"


def get_default_azure_credential_error_types() -> tuple[type[Exception], ...]:
    """Return the expected Azure SDK exception types for credential operations."""
    try:
        from azure.core.exceptions import ClientAuthenticationError
        from azure.identity import CredentialUnavailableError
    except ImportError:
        return ()

    return CredentialUnavailableError, ClientAuthenticationError


def _default_credential_kwargs(*, client_id: Optional[str]) -> dict[str, Any]:
    """Build the shared DefaultAzureCredential kwargs for sync and async factories."""
    credential_kwargs: dict[str, Any] = {}
    if client_id:
        credential_kwargs["managed_identity_client_id"] = client_id
    return credential_kwargs


def create_default_azure_credential(
    *,
    client_id: Optional[str],
    logger: LoggingPort,
) -> AzureCredentialProtocol:
    """Create the canonical Azure DefaultAzureCredential for ORB Azure flows."""
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        logger.error(format_import_error("azure-identity", exc))
        raise

    credential_kwargs = _default_credential_kwargs(client_id=client_id)

    try:
        credential = DefaultAzureCredential(**credential_kwargs)
    except ImportError as exc:
        logger.error(format_import_error("azure-identity", exc))
        raise
    logger.debug("Azure DefaultAzureCredential initialised")
    return credential


# Init-scoped credentials keyed by managed-identity client ID (``None`` = no
# explicit identity).  One ``orb init`` run resolves each identity once and
# ``close_shared_credentials`` releases them when the run ends.  Management
# clients built on a shared credential must not close it: the credential
# outlives every client created from it.
_shared_lock = threading.Lock()
_shared_credentials: dict[Optional[str], AzureCredentialProtocol] = {}


def get_shared_default_azure_credential(
    client_id: Optional[str], logger: Optional[LoggingPort] = None
) -> AzureCredentialProtocol:
    """Return the shared DefaultAzureCredential for ``client_id``, creating it on first use."""
    with _shared_lock:
        credential = _shared_credentials.get(client_id)
        if credential is None:
            if logger is None:
                from orb.infrastructure.adapters.logging_adapter import LoggingAdapter

                logger = LoggingAdapter()
            credential = create_default_azure_credential(client_id=client_id, logger=logger)
            _shared_credentials[client_id] = credential
        return credential


def close_shared_credentials() -> None:
    """Close every shared credential once and forget them."""
    with _shared_lock:
        credentials = list(_shared_credentials.values())
        _shared_credentials.clear()
    for credential in credentials:
        with contextlib.suppress(Exception):
            credential.close()


_suppress_lock = threading.Lock()
_suppress_depth = 0
_suppress_saved_level = logging.NOTSET


@contextlib.contextmanager
def suppress_azure_identity_warnings() -> Iterator[None]:
    """Hide ``azure.identity`` credential-chain warnings for the duration of the block.

    The chain logs a multi-line warning for every credential it tries before the
    one that works; init reports a short one-line error instead.  The level is
    raised by the first active block and restored by the last, so overlapping
    blocks on different threads never leave it raised.  A logger-level filter
    cannot do this: the warnings come from child loggers, which bypass it.
    """
    global _suppress_depth, _suppress_saved_level
    identity_logger = logging.getLogger("azure.identity")
    with _suppress_lock:
        if _suppress_depth == 0:
            _suppress_saved_level = identity_logger.level
            identity_logger.setLevel(logging.ERROR)
        _suppress_depth += 1
    try:
        yield
    finally:
        with _suppress_lock:
            _suppress_depth -= 1
            if _suppress_depth == 0:
                identity_logger.setLevel(_suppress_saved_level)


def create_default_azure_credential_async(
    *,
    client_id: Optional[str],
    logger: LoggingPort,
) -> AsyncAzureCredentialProtocol:
    """Create the canonical async Azure DefaultAzureCredential for ORB Azure flows."""
    try:
        from azure.identity.aio import DefaultAzureCredential
    except ImportError as exc:
        logger.error(format_import_error("azure-identity", exc))
        raise

    credential_kwargs = _default_credential_kwargs(client_id=client_id)

    try:
        credential = DefaultAzureCredential(**credential_kwargs)
    except ImportError as exc:
        logger.error(format_import_error("azure-identity", exc))
        raise
    logger.debug("Async Azure DefaultAzureCredential initialised")
    return credential


class DefaultAzureAccessTokenProvider(AzureAccessTokenProviderProtocol):
    """Resolve Azure access tokens with short-lived credentials."""

    def __init__(
        self,
        *,
        client_id: Optional[str],
        logger: LoggingPort,
    ) -> None:
        self._client_id = client_id
        self._logger = logger

    def get_access_token(self, scope: str) -> str:
        """Create a short-lived credential, fetch a token, then close it."""
        credential = create_default_azure_credential(
            client_id=self._client_id,
            logger=self._logger,
        )
        try:
            token = credential.get_token(scope)
            return token.token
        finally:
            credential.close()

    def get_auth_error_types(self) -> tuple[type[Exception], ...]:
        """Return Azure SDK and ImportError types for credential failures."""
        return ImportError, *get_default_azure_credential_error_types()


class AsyncDefaultAzureAccessTokenProvider(AsyncAzureAccessTokenProviderProtocol):
    """Resolve Azure access tokens with short-lived async credentials."""

    def __init__(
        self,
        *,
        client_id: Optional[str],
        logger: LoggingPort,
    ) -> None:
        self._client_id = client_id
        self._logger = logger

    async def get_access_token(self, scope: str) -> str:
        """Create a short-lived async credential, fetch a token, then close it."""
        credential = create_default_azure_credential_async(
            client_id=self._client_id,
            logger=self._logger,
        )
        try:
            token = await credential.get_token(scope)
            return token.token
        finally:
            await credential.close()

    def get_auth_error_types(self) -> tuple[type[Exception], ...]:
        """Return Azure SDK and ImportError types for credential failures."""
        return ImportError, *get_default_azure_credential_error_types()
