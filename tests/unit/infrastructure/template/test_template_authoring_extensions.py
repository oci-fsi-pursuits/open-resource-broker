"""Authoring must retain provider extensions without provider branches in handlers."""

from pydantic import BaseModel

from orb.infrastructure.registry.template_extension_registry import TemplateExtensionRegistry
from orb.infrastructure.template.factories import TemplateDTOFactory


class ExampleExtension(BaseModel):
    placement: str | None = None
    replicas: int = 1


def test_authoring_keeps_extension_and_canonical_generic_fields(monkeypatch):
    monkeypatch.setattr(
        TemplateExtensionRegistry,
        "create_extension_config",
        lambda provider_type, data: (
            ExampleExtension(**data) if provider_type == "example" else None
        ),
    )
    factory = TemplateDTOFactory()
    created = factory.from_config(
        {
            "template_id": "worker",
            "provider_type": "example",
            "placement": "zone-1",
            "replicas": 2,
            "machine_image": "image",
            "machine_bootstrap": "bootstrap",
            "max_machines": 3,
        }
    )
    assert isinstance(created.provider_config, ExampleExtension)
    assert created.provider_config.placement == "zone-1"
    assert created.image_id == "image"
    assert created.user_data == "bootstrap"
    assert created.max_instances == 3

    updated = factory.from_config({**created.model_dump(), "replicas": 4})
    assert updated.provider_config.placement == "zone-1"
    assert updated.provider_config.replicas == 4
    assert updated.user_data == "bootstrap"
