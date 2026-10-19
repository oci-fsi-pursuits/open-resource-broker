"""Shared Azure strategy test fixtures."""

from unittest.mock import MagicMock

import pytest

from orb.providers.azure.configuration.config import AzureProviderConfig
from tests.providers.azure.strategy_test_support import build_strategy_harness


@pytest.fixture(autouse=True)
def _close_shared_azure_credentials():
    """Drop init-scoped credentials so tests never see each other's identities."""
    from orb.providers.azure.infrastructure.credential_factory import close_shared_credentials

    close_shared_credentials()
    yield
    close_shared_credentials()


@pytest.fixture
def azure_config():
    return AzureProviderConfig(
        subscription_id="12345678-1234-1234-1234-123456789012",
        resource_group="test-rg",
        region="eastus2",
    )


@pytest.fixture
def logger():
    return MagicMock()


@pytest.fixture
def strategy_harness(azure_config, logger):
    return build_strategy_harness(config=azure_config, logger=logger)


@pytest.fixture
def strategy(strategy_harness):
    return strategy_harness.strategy
