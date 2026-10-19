"""Azure init discovery uses the selected identity and subscription."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from orb.providers.azure.services import init_discovery

_CREDENTIAL_FACTORY = (
    "orb.providers.azure.infrastructure.credential_factory.create_default_azure_credential"
)


def test_subscription_discovery_closes_client_but_keeps_shared_credential(monkeypatch) -> None:
    credential = MagicMock()
    client = MagicMock()
    client.subscriptions.list.return_value = [
        MagicMock(subscription_id="sub-a", display_name="Zebra"),
        MagicMock(subscription_id="sub-b", display_name="Alpha"),
    ]
    credential_factory = MagicMock(return_value=credential)
    monkeypatch.setattr(_CREDENTIAL_FACTORY, credential_factory)
    monkeypatch.setattr(
        "azure.mgmt.resource.subscriptions.SubscriptionClient", MagicMock(return_value=client)
    )

    assert init_discovery.list_subscriptions("managed-id") == [
        ("sub-b", "Alpha"),
        ("sub-a", "Zebra"),
    ]
    assert credential_factory.call_args.kwargs["client_id"] == "managed-id"
    client.close.assert_called_once()
    credential.close.assert_not_called()


def test_resource_group_and_location_discovery_use_subscription(monkeypatch) -> None:
    credential = MagicMock()
    resource_client = MagicMock()
    group = MagicMock()
    group.name = "workers"
    resource_client.resource_groups.list.return_value = [group]
    subscription_client = MagicMock()
    location = MagicMock()
    location.name = "uksouth"
    location.display_name = "UK South"
    location.metadata.region_type = "Physical"
    logical_location = MagicMock(name="europe", display_name="Europe")
    logical_location.metadata.region_type = "Logical"
    subscription_client.subscriptions.list_locations.return_value = [location, logical_location]
    credential_factory = MagicMock(return_value=credential)
    monkeypatch.setattr(_CREDENTIAL_FACTORY, credential_factory)
    resource_factory = MagicMock(return_value=resource_client)
    subscription_factory = MagicMock(return_value=subscription_client)
    monkeypatch.setattr("azure.mgmt.resource.resources.ResourceManagementClient", resource_factory)
    monkeypatch.setattr(
        "azure.mgmt.resource.subscriptions.SubscriptionClient", subscription_factory
    )

    assert init_discovery.list_resource_groups(None, "sub-a") == [("workers", "workers")]
    assert init_discovery.list_locations(None, "sub-a") == [("uksouth", "UK South")]
    assert resource_factory.call_args.args[1] == "sub-a"
    subscription_client.subscriptions.list_locations.assert_called_once_with("sub-a")
    credential_factory.assert_called_once()
    credential.close.assert_not_called()


def test_discovery_calls_for_one_identity_share_a_credential(monkeypatch) -> None:
    credential_factory = MagicMock(side_effect=lambda **_: MagicMock())
    monkeypatch.setattr(_CREDENTIAL_FACTORY, credential_factory)
    monkeypatch.setattr(
        "azure.mgmt.resource.subscriptions.SubscriptionClient",
        MagicMock(side_effect=lambda *_a, **_k: MagicMock()),
    )
    monkeypatch.setattr(
        "azure.mgmt.resource.resources.ResourceManagementClient",
        MagicMock(side_effect=lambda *_a, **_k: MagicMock()),
    )

    init_discovery.list_subscriptions("identity-a")
    init_discovery.list_resource_groups("identity-a", "sub-a")
    init_discovery.list_locations("identity-a", "sub-a")
    init_discovery.list_subscriptions("identity-b")

    assert [call.kwargs["client_id"] for call in credential_factory.call_args_list] == [
        "identity-a",
        "identity-b",
    ]


def test_closing_management_clients_leaves_the_shared_credential_open() -> None:
    """Real SDK clients: ``client.close()`` must not close the credential passed to them."""
    from azure.mgmt.resource.resources import ResourceManagementClient
    from azure.mgmt.resource.subscriptions import SubscriptionClient

    class RecordingCredential:
        closed = 0

        def get_token(self, *scopes, **kwargs):
            return SimpleNamespace(token="token", expires_on=4102444800)

        def close(self):
            self.closed += 1

    credential = RecordingCredential()
    SubscriptionClient(credential).close()  # type: ignore[arg-type]
    ResourceManagementClient(credential, "00000000-0000-0000-0000-000000000001").close()  # type: ignore[arg-type]
    with SubscriptionClient(credential):  # type: ignore[arg-type]
        pass

    assert credential.closed == 0


def test_chain_warnings_are_hidden_only_while_discovering(monkeypatch, caplog) -> None:
    identity_logger = logging.getLogger("azure.identity")
    chain_logger = logging.getLogger("azure.identity._credentials.chained")
    previous = identity_logger.level
    seen_levels: list[int] = []

    def noisy_list():
        seen_levels.append(identity_logger.level)
        chain_logger.warning("DefaultAzureCredential failed to retrieve a token")
        return []

    client = MagicMock()
    client.subscriptions.list.side_effect = noisy_list
    monkeypatch.setattr(_CREDENTIAL_FACTORY, MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(
        "azure.mgmt.resource.subscriptions.SubscriptionClient", MagicMock(return_value=client)
    )

    with caplog.at_level(logging.WARNING):
        init_discovery.list_subscriptions(None)

    assert seen_levels == [logging.ERROR]
    assert "failed to retrieve a token" not in caplog.text
    assert identity_logger.level == previous


# ---------------------------------------------------------------------------
# Full interactive init
# ---------------------------------------------------------------------------


class _CountingCredential:
    created = 0
    closed = 0

    def __init__(self, *args, **kwargs):
        type(self).created += 1

    def get_token(self, *scopes, **kwargs):
        return SimpleNamespace(token="token", expires_on=4102444800)

    def close(self):
        type(self).closed += 1


@pytest.fixture
def fake_azure_sdk(monkeypatch):
    import azure.identity

    _CountingCredential.created = 0
    _CountingCredential.closed = 0
    subscription_client = MagicMock()
    subscription_client.subscriptions.list.return_value = [
        SimpleNamespace(subscription_id="11111111-2222-3333-4444-555555555555", display_name="One")
    ]
    subscription_client.subscriptions.list_locations.return_value = [
        SimpleNamespace(
            name="eastus2",
            display_name="East US 2",
            metadata=SimpleNamespace(region_type="Physical"),
        )
    ]
    resource_client = MagicMock()
    resource_client.resource_groups.list.return_value = [SimpleNamespace(name="workers")]
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", _CountingCredential)
    monkeypatch.setattr(
        "azure.mgmt.resource.subscriptions.SubscriptionClient",
        MagicMock(return_value=subscription_client),
    )
    monkeypatch.setattr(
        "azure.mgmt.resource.resources.ResourceManagementClient",
        MagicMock(return_value=resource_client),
    )
    return _CountingCredential


def test_full_init_resolves_one_credential_and_closes_it_once(fake_azure_sdk, tmp_path) -> None:
    from tests.utilities.init_flow import run_interactive_init

    assert run_interactive_init("azure", tmp_path) == 0

    assert fake_azure_sdk.created == 1
    assert fake_azure_sdk.closed == 1


def test_second_init_run_resolves_a_fresh_credential(fake_azure_sdk, tmp_path) -> None:
    from tests.utilities.init_flow import run_interactive_init

    run_interactive_init("azure", tmp_path)
    run_interactive_init("azure", tmp_path)

    assert fake_azure_sdk.created == 2
    assert fake_azure_sdk.closed == 2


def test_cli_init_writes_azure_config_and_closes_one_credential(fake_azure_sdk, tmp_path) -> None:
    from tests.utilities.init_flow import run_cli_init

    code, config = run_cli_init("azure", tmp_path)

    assert code == 0
    (provider,) = config["provider"]["providers"]
    assert provider["type"] == "azure"
    assert provider["config"]["subscription_id"] == "11111111-2222-3333-4444-555555555555"
    assert provider["config"]["resource_group"] == "workers"
    assert provider["config"]["region"] == "eastus2"
    assert config["provider"]["default_provider_instance"] == provider["name"]
    assert fake_azure_sdk.created == 1
    assert fake_azure_sdk.closed == 1
