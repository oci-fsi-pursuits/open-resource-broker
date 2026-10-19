"""Shared fixtures for the GCP provider test tree."""

import pytest


@pytest.fixture(autouse=True)
def _clear_cached_gcp_credentials():
    """Drop init-scoped ADC so tests never see each other's credentials."""
    from orb.providers.gcp.services.init_discovery import clear_default_credentials

    clear_default_credentials()
    yield
    clear_default_credentials()
