"""OCI-specific HostFactory aliases."""

from typing import Any


class OCIFieldMapping:
    def prepare_output_fields(self, template: dict[str, Any]) -> dict[str, Any]:
        """Expose persisted OCI extensions without changing other providers."""
        provider_config = template.get("provider_config")
        if isinstance(provider_config, dict):
            return {**provider_config, **template}
        return template

    def get_mappings(self) -> dict[str, str]:
        return {
            "subnetId": "subnet_ids",
            "subnetIds": "subnet_ids",
            "securityGroupIds": "security_group_ids",
            "userDataScript": "machine_bootstrap",
            "compartmentId": "compartment_id",
            "availabilityDomain": "availability_domain",
            "computeClusterId": "compute_cluster_id",
            "agentConfig": "agent_config",
            "shape": "shape",
            "shapeConfig": "shape_config",
            "ocpus": "ocpus",
            "memoryInGBs": "memory_gbs",
            "bootVolumeSizeInGBs": "boot_volume_gbs",
            "capacityType": "capacity_type",
            "fallbackToOndemand": "fallback_to_ondemand",
            "preemptiblePreserveBootVolume": "preemptible_preserve_boot_volume",
            "sshAuthorizedKeys": "ssh_authorized_keys",
            "formFactor": "form_factor",
            "cpuVendor": "cpu_vendor",
            "generation": "generation",
        }

    def apply_defaults(self, mapped: dict) -> dict:
        mapped.setdefault("max_machines", 1)
        return mapped

    def derive_attributes(self, machine_type: str | None) -> dict[str, list[str]] | None:
        # Flex shapes do not determine CPU/memory without shape_config.
        return None
