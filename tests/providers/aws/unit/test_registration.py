"""Unit tests for create_aws_strategy — console injection."""

from unittest.mock import MagicMock, patch


def test_create_aws_strategy_injects_console_into_strategy():
    """ConsolePort from DI container must be passed to AWSProviderStrategy, not fall back to NullConsoleAdapter."""
    from orb.infrastructure.adapters.null_console_adapter import NullConsoleAdapter
    from orb.providers.aws.registration import create_aws_strategy

    mock_console = MagicMock()
    mock_config_port = MagicMock()

    def mock_container_get(port):
        port_name = str(port)
        if "Console" in port_name:
            return mock_console
        return mock_config_port

    mock_container = MagicMock()
    mock_container.get.side_effect = mock_container_get

    # get_container is imported locally inside create_aws_strategy — patch at source
    with patch("orb.infrastructure.di.container.get_container", return_value=mock_container):
        strategy = create_aws_strategy({"region": "us-east-1"})

    assert strategy._console is mock_console
    assert not isinstance(strategy._console, NullConsoleAdapter)


def test_create_aws_strategy_handles_missing_console_gracefully():
    """If ConsolePort lookup fails, strategy is still created (console falls back to None)."""
    from orb.providers.aws.registration import create_aws_strategy

    # get_container is imported locally — patch at source
    with patch(
        "orb.infrastructure.di.container.get_container", side_effect=Exception("DI not ready")
    ):
        strategy = create_aws_strategy({"region": "us-east-1"})

    assert strategy is not None


def _create_strategy_capturing_health_checks(aws_client_cls):
    """Run create_aws_strategy and return the health checks it registered by name."""
    from orb.domain.base.ports.health_check_port import HealthCheckPort
    from orb.providers.aws.registration import create_aws_strategy

    health_check = MagicMock()
    container = MagicMock()
    container.get.side_effect = lambda port: (
        health_check if port is HealthCheckPort else MagicMock()
    )
    with (
        patch("orb.infrastructure.di.container.get_container", return_value=container),
        patch("orb.providers.aws.strategy.aws_provider_strategy.AWSClient", aws_client_cls),
    ):
        strategy = create_aws_strategy({"region": "us-east-1"})
    checks = {call.args[0]: call.args[1] for call in health_check.register_check.call_args_list}
    return strategy, checks


def test_create_aws_strategy_registers_health_checks_without_building_client():
    aws_client_cls = MagicMock()

    _, checks = _create_strategy_capturing_health_checks(aws_client_cls)

    assert set(checks) == {"aws", "ec2"}
    aws_client_cls.assert_not_called()


def test_registered_health_checks_build_the_client_on_first_execution_only():
    aws_client_cls = MagicMock()
    aws_client_cls.return_value.sts_client.get_caller_identity.return_value = {
        "Account": "123456789012",
        "UserId": "AIDAEXAMPLE",
        "Arn": "arn:aws:iam::123456789012:user/example",
    }
    aws_client_cls.return_value.ec2_client.describe_instances.return_value = {"Reservations": []}
    strategy, checks = _create_strategy_capturing_health_checks(aws_client_cls)

    with patch("orb.providers.aws.strategy.aws_provider_strategy.AWSClient", aws_client_cls):
        aws_status = checks["aws"]()
        ec2_status = checks["ec2"]()

    assert aws_status.status == "healthy"
    assert ec2_status.status == "healthy"
    aws_client_cls.assert_called_once()
    assert strategy.aws_client is aws_client_cls.return_value


def test_unbuildable_client_does_not_gate_readiness_and_is_not_rebuilt_every_poll():
    from orb.monitoring.health import HealthCheck

    aws_client_cls = MagicMock(side_effect=RuntimeError("no credentials"))
    _, checks = _create_strategy_capturing_health_checks(aws_client_cls)
    health_check = HealthCheck(MagicMock())
    for name, check in checks.items():
        health_check.register_check(name, check, kind="core")
    without_aws = HealthCheck(MagicMock())
    without_aws.run_all_checks()
    baseline = without_aws.get_readiness()["status"]

    with patch("orb.providers.aws.strategy.aws_provider_strategy.AWSClient", aws_client_cls):
        for _ in range(3):
            health_check.run_all_checks()
        readiness = health_check.get_readiness()

    assert readiness["status"] == baseline
    assert checks["aws"]().status == "unknown"
    assert checks["ec2"]().status == "unknown"
    aws_client_cls.assert_called_once()


def test_concurrent_health_checks_build_one_client():
    import threading
    import time

    built = []

    def slow_client(*_args, **_kwargs):
        built.append(1)
        time.sleep(0.1)
        client = MagicMock()
        client.sts_client.get_caller_identity.return_value = {
            "Account": "1",
            "UserId": "u",
            "Arn": "a",
        }
        client.ec2_client.describe_instances.return_value = {"Reservations": []}
        return client

    aws_client_cls = MagicMock(side_effect=slow_client)
    _, checks = _create_strategy_capturing_health_checks(aws_client_cls)
    with patch("orb.providers.aws.strategy.aws_provider_strategy.AWSClient", aws_client_cls):
        threads = [threading.Thread(target=check) for check in checks.values() for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert len(built) == 1
