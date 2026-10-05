"""OCI template with provider-specific launch configuration."""

from typing import Any
from pydantic import model_validator
from orb.domain.template.template_aggregate import Template
from orb.providers.oci.configuration.template_extension import OCITemplateExtensionConfig


class OCITemplate(Template, OCITemplateExtensionConfig):
    """Preserve OCI fields across the template repository and scheduler."""

    provider_type: str = "oci"
    provider_api: str = "OCICompute"

    @model_validator(mode="before")
    @classmethod
    def normalize_shape(cls, data: Any) -> Any:
        """Expose single-shape input through ORB's canonical machine_types field."""
        if isinstance(data, dict) and not data.get("machine_types"):
            shape = data.get("shape") or data.get("machine_type") or data.get("instance_type")
            if shape:
                return {**data, "machine_types": {shape: 1}}
        return data
