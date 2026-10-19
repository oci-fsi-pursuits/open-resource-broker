"""Read-only Azure account discovery for the interactive init wizard."""

from orb.providers.azure.infrastructure.credential_factory import (
    get_shared_default_azure_credential,
    suppress_azure_identity_warnings,
)


def list_subscriptions(client_id: str | None) -> list[tuple[str, str]]:
    """List subscriptions visible to the selected Azure identity."""
    from azure.mgmt.resource.subscriptions import SubscriptionClient

    credential = get_shared_default_azure_credential(client_id)
    client = SubscriptionClient(credential)
    try:
        with suppress_azure_identity_warnings():
            subscriptions = [
                (
                    subscription.subscription_id,
                    subscription.display_name or subscription.subscription_id,
                )
                for subscription in client.subscriptions.list()
                if subscription.subscription_id
            ]
        return sorted(subscriptions, key=lambda item: (item[1].casefold(), item[0]))
    finally:
        client.close()


def list_resource_groups(client_id: str | None, subscription_id: str) -> list[tuple[str, str]]:
    """List resource groups in the selected subscription."""
    from azure.mgmt.resource.resources import ResourceManagementClient

    credential = get_shared_default_azure_credential(client_id)
    client = ResourceManagementClient(credential, subscription_id)
    try:
        with suppress_azure_identity_warnings():
            return sorted(
                (group.name, group.name) for group in client.resource_groups.list() if group.name
            )
    finally:
        client.close()


def list_locations(client_id: str | None, subscription_id: str) -> list[tuple[str, str]]:
    """List locations available to the selected subscription."""
    from azure.mgmt.resource.subscriptions import SubscriptionClient

    credential = get_shared_default_azure_credential(client_id)
    client = SubscriptionClient(credential)
    try:
        with suppress_azure_identity_warnings():
            return sorted(
                (location.name, location.display_name or location.name)
                for location in client.subscriptions.list_locations(subscription_id)
                if location.name
                and location.metadata is not None
                and location.metadata.region_type == "Physical"
            )
    finally:
        client.close()
