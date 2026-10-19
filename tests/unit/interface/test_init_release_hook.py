"""``orb init`` releases provider init resources once per run, whatever the outcome."""

import argparse
import asyncio
from unittest.mock import MagicMock, patch

import pytest

import orb.interface.init_command_handler as init_handler
from orb.providers.base.strategy.provider_strategy import ProviderStrategy


def _strategy_class(name: str) -> MagicMock:
    strategy = MagicMock(name=name)
    strategy.release_init_resources = MagicMock()
    return strategy


def _container(strategies: dict[str, MagicMock]) -> MagicMock:
    registry = MagicMock()
    registry._get_type_registration.side_effect = lambda provider_type: MagicMock(
        strategy_class=strategies[provider_type]
    )
    container = MagicMock()
    container.get.return_value = registry
    return container


def _run_init(container: MagicMock, interactive_setup, tmp_path) -> int:
    args = argparse.Namespace(
        _container=container,
        config_dir=str(tmp_path / "config"),
        scripts_dir=None,
        force=True,
        non_interactive=False,
    )
    with (
        patch.object(init_handler, "_interactive_setup", interactive_setup),
        patch.object(init_handler, "_create_directories"),
        patch.object(init_handler, "_write_config_file"),
        patch.object(init_handler, "_copy_scripts"),
    ):
        return asyncio.run(init_handler.handle_init(args))


def _setup_resolving(
    container: MagicMock, *provider_types: str, error: BaseException | None = None
):
    def _setup(_container, used_provider_types):
        for provider_type in provider_types:
            used_provider_types.add(provider_type)
        if error is not None:
            raise error
        return {"scheduler_type": "default", "providers": []}

    return _setup


def test_default_release_hook_is_a_no_op() -> None:
    assert ProviderStrategy.release_init_resources() is None


def test_release_called_once_per_provider_used_on_success(tmp_path) -> None:
    aws, gcp = _strategy_class("aws"), _strategy_class("gcp")
    container = _container({"aws": aws, "gcp": gcp, "azure": _strategy_class("azure")})

    result = _run_init(container, _setup_resolving(container, "aws", "gcp", "aws"), tmp_path)

    assert result == 0
    aws.release_init_resources.assert_called_once_with()
    gcp.release_init_resources.assert_called_once_with()


@pytest.mark.parametrize("error", [RuntimeError("boom"), KeyboardInterrupt(), EOFError()])
def test_release_called_when_init_fails_or_is_cancelled(tmp_path, error) -> None:
    aws = _strategy_class("aws")
    container = _container({"aws": aws})

    result = _run_init(container, _setup_resolving(container, "aws", error=error), tmp_path)

    assert result == 1
    aws.release_init_resources.assert_called_once_with()


def test_failing_release_does_not_change_the_result(tmp_path) -> None:
    aws, gcp = _strategy_class("aws"), _strategy_class("gcp")
    aws.release_init_resources.side_effect = RuntimeError("close failed")
    container = _container({"aws": aws, "gcp": gcp})

    result = _run_init(container, _setup_resolving(container, "aws", "gcp"), tmp_path)

    assert result == 0
    gcp.release_init_resources.assert_called_once_with()


def test_failing_release_does_not_replace_the_original_failure(tmp_path) -> None:
    aws = _strategy_class("aws")
    aws.release_init_resources.side_effect = RuntimeError("close failed")
    container = _container({"aws": aws})

    result = _run_init(
        container, _setup_resolving(container, "aws", error=ValueError("setup failed")), tmp_path
    )

    assert result == 1


def test_providers_without_a_release_hook_are_skipped(tmp_path) -> None:
    legacy = MagicMock(spec=[])
    container = _container({"legacy": legacy})

    assert _run_init(container, _setup_resolving(container, "legacy"), tmp_path) == 0


def test_providers_are_not_carried_over_to_the_next_run(tmp_path) -> None:
    aws, gcp = _strategy_class("aws"), _strategy_class("gcp")
    container = _container({"aws": aws, "gcp": gcp})

    _run_init(container, _setup_resolving(container, "aws"), tmp_path)
    _run_init(container, _setup_resolving(container, "gcp"), tmp_path)

    aws.release_init_resources.assert_called_once_with()
    gcp.release_init_resources.assert_called_once_with()
