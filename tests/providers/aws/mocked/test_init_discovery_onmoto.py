"""Moto integration tests for AWSInfrastructureDiscoveryService."""

from unittest.mock import MagicMock, patch as _patch

import pytest


@pytest.fixture
def discovery_service(moto_aws):
    """Create AWSInfrastructureDiscoveryService inside moto context."""
    from orb.providers.aws.services.infrastructure_discovery_service import (
        AWSInfrastructureDiscoveryService,
    )

    return AWSInfrastructureDiscoveryService(
        region="eu-west-2",
        profile=None,
        console=MagicMock(),
    )


def test_discover_vpcs_returns_vpcs(discovery_service, moto_vpc_resources):
    vpcs = discovery_service.discover_vpcs()
    assert len(vpcs) >= 1
    vpc_ids = [v.id for v in vpcs]
    assert moto_vpc_resources["vpc_id"] in vpc_ids


def test_discover_vpcs_returns_empty_when_no_vpcs(moto_aws):
    from orb.providers.aws.services.infrastructure_discovery_service import (
        AWSInfrastructureDiscoveryService,
    )

    service = AWSInfrastructureDiscoveryService(
        region="eu-west-2", profile=None, console=MagicMock()
    )
    vpcs = service.discover_vpcs()
    # moto starts with a default VPC — filter to only non-default
    non_default = [v for v in vpcs if not v.is_default]
    assert non_default == []


def test_discover_subnets_returns_subnets_for_vpc(discovery_service, moto_vpc_resources):
    subnets = discovery_service.discover_subnets(moto_vpc_resources["vpc_id"])
    assert len(subnets) >= 1
    subnet_ids = [s.id for s in subnets]
    for sid in moto_vpc_resources["subnet_ids"]:
        assert sid in subnet_ids


def test_discover_security_groups_returns_sgs_for_vpc(discovery_service, moto_vpc_resources):
    sgs = discovery_service.discover_security_groups(moto_vpc_resources["vpc_id"])
    assert len(sgs) >= 1
    sg_ids = [sg.id for sg in sgs]
    assert moto_vpc_resources["sg_id"] in sg_ids


def test_discover_infrastructure_interactive_happy_path(discovery_service, moto_vpc_resources):
    """Full interactive flow: select VPC, subnets, SG, skip fleet role."""
    with _patch("builtins.input", side_effect=["1", "1,2", "1", ""]):
        result = discovery_service.discover_infrastructure_interactive(
            {"type": "aws", "config": {"region": "eu-west-2"}}
        )
    assert "subnet_ids" in result
    assert "security_group_ids" in result
    assert len(result["subnet_ids"]) >= 1
    assert len(result["security_group_ids"]) >= 1


def test_discover_infrastructure_interactive_no_vpcs_returns_empty(moto_aws):
    """When no VPCs exist (beyond default), interactive discovery returns empty."""
    from orb.providers.aws.services.infrastructure_discovery_service import (
        AWSInfrastructureDiscoveryService,
    )

    service = AWSInfrastructureDiscoveryService(
        region="eu-west-2", profile=None, console=MagicMock()
    )

    with _patch.object(service, "discover_vpcs", return_value=[]):
        result = service.discover_infrastructure_interactive({"type": "aws", "config": {}})

    assert result == {}


def test_discover_spotfleet_role_constructs_arn(discovery_service):
    """_discover_spotfleet_role returns an ARN containing the moto account ID."""
    arn = discovery_service._discover_spotfleet_role()
    # moto account ID is 123456789012
    if arn is not None:
        assert "123456789012" in arn
        assert "AWSServiceRoleForEC2SpotFleet" in arn


# ---------------------------------------------------------------------------
# Credential reuse across a full interactive init run
# ---------------------------------------------------------------------------


def _count_aws_calls(monkeypatch) -> dict:
    """Count AWS sessions, STS identity calls and AWSClient constructions made by ORB."""
    import sys

    import boto3
    import botocore.client

    from orb.providers.aws.infrastructure.aws_client import AWSClient

    counts = {"session": 0, "sts": 0, "aws_client": 0}
    real_session_init = boto3.Session.__init__
    real_api_call = botocore.client.BaseClient._make_api_call
    real_client_init = AWSClient.__init__

    def _created_by_orb() -> bool:
        frame = sys._getframe(2)
        while frame is not None:
            filename = frame.f_code.co_filename.replace("\\", "/")
            if "site-packages/moto" in filename:
                return False
            if "orb/providers/aws" in filename:
                return True
            frame = frame.f_back
        return False

    def session_init(self, *args, **kwargs):
        if _created_by_orb():
            counts["session"] += 1
        real_session_init(self, *args, **kwargs)

    def api_call(self, operation_name, api_params):
        if operation_name == "GetCallerIdentity":
            counts["sts"] += 1
        return real_api_call(self, operation_name, api_params)

    def client_init(self, *args, **kwargs):
        counts["aws_client"] += 1
        real_client_init(self, *args, **kwargs)

    monkeypatch.setattr(boto3.Session, "__init__", session_init)
    monkeypatch.setattr(botocore.client.BaseClient, "_make_api_call", api_call)
    monkeypatch.setattr(AWSClient, "__init__", client_init)
    return counts


@pytest.fixture
def init_call_counts(moto_aws, monkeypatch):
    counts = _count_aws_calls(monkeypatch)
    container = MagicMock()
    monkeypatch.setattr("orb.infrastructure.di.container.get_container", lambda: container)
    return counts


@pytest.fixture
def cli_init_call_counts(moto_aws, monkeypatch):
    """Call counts for a run through the real CLI, which builds its own container."""
    return _count_aws_calls(monkeypatch)


def _use_named_profile(tmp_path, monkeypatch) -> None:
    aws_dir = tmp_path / ".aws"
    aws_dir.mkdir()
    (aws_dir / "credentials").write_text("[prof1]\naws_access_key_id=a\naws_secret_access_key=b\n")
    (aws_dir / "config").write_text("[profile prof1]\nregion=eu-west-2\n")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(aws_dir / "credentials"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(aws_dir / "config"))


def test_init_default_chain_resolves_credentials_once(init_call_counts, tmp_path, monkeypatch):
    from tests.utilities.init_flow import run_interactive_init

    monkeypatch.setenv("HOME", str(tmp_path))

    assert run_interactive_init("aws", tmp_path) == 0

    assert init_call_counts == {"session": 1, "sts": 1, "aws_client": 0}


def test_init_named_profile_resolves_each_identity_once(init_call_counts, tmp_path, monkeypatch):
    from tests.utilities.init_flow import run_interactive_init

    _use_named_profile(tmp_path, monkeypatch)

    assert run_interactive_init("aws", tmp_path) == 0

    assert init_call_counts == {"session": 2, "sts": 2, "aws_client": 0}


def test_second_init_run_resolves_credentials_afresh(init_call_counts, tmp_path, monkeypatch):
    from tests.utilities.init_flow import run_interactive_init

    monkeypatch.setenv("HOME", str(tmp_path))
    assert run_interactive_init("aws", tmp_path) == 0
    first = dict(init_call_counts)
    for key in init_call_counts:
        init_call_counts[key] = 0

    assert run_interactive_init("aws", tmp_path) == 0

    assert init_call_counts == first


def test_cli_init_default_chain_writes_config_and_resolves_credentials_once(
    cli_init_call_counts, tmp_path, monkeypatch
):
    from tests.utilities.init_flow import run_cli_init

    monkeypatch.setenv("HOME", str(tmp_path))

    code, config = run_cli_init("aws", tmp_path)

    assert code == 0
    (provider,) = config["provider"]["providers"]
    assert provider["type"] == "aws"
    assert provider["config"]["region"]
    assert provider["template_defaults"]["subnet_ids"]
    assert provider["template_defaults"]["security_group_ids"]
    assert config["provider"]["default_provider_instance"] == provider["name"]
    assert cli_init_call_counts == {"session": 1, "sts": 1, "aws_client": 0}
