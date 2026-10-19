"""Provider strategy lookup and release of provider-held credentials and clients."""

from typing import Any, Optional

from orb.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


def resolve_provider_strategy_class(
    provider_type: str, registry: Any = None, container: Any = None
) -> Optional[type]:
    """Return the strategy CLASS registered for a provider type, or ``None``."""
    try:
        if registry is None and container is not None:
            from orb.domain.base.ports.provider_registry_port import ProviderRegistryPort

            registry = container.get(ProviderRegistryPort)
        if registry is None:
            return None
        # Ensure the provider type is registered so its class is available.
        registry.ensure_provider_type_registered(provider_type)
        reg = registry._get_type_registration(provider_type)
        return getattr(reg, "strategy_class", None)
    except Exception:
        return None


def release_provider_init_resources(container: Any, provider_types: set[str]) -> None:
    """Let each provider type drop the credentials and clients cached while it was queried.

    Failures are logged and swallowed so cleanup never changes a command's result.
    """
    if container is None:
        return
    for provider_type in sorted(provider_types):
        try:
            strategy_class = resolve_provider_strategy_class(provider_type, container=container)
            release = getattr(strategy_class, "release_init_resources", None)
            if release is not None:
                release()
        except Exception as e:
            logger.debug("Could not release init resources for %s: %s", provider_type, e)
