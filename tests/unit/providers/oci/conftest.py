"""Keep OCI defaults registration local to each test."""

import pytest

from orb.providers.registry.defaults_loader_registry import DefaultsLoaderRegistry


@pytest.fixture(autouse=True)
def isolate_defaults_registration(monkeypatch):
    """A partial OCI registration must not affect another provider's tests."""
    monkeypatch.setattr(DefaultsLoaderRegistry, "_store", DefaultsLoaderRegistry.all())
