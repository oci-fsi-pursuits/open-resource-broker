"""Drive the interactive ``orb init`` handler with scripted answers."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any, Callable, Optional
from unittest.mock import MagicMock, patch

import orb.interface.init_command_handler as init_handler
from orb.domain.base.ports.console_port import ConsolePort
from orb.domain.base.ports.provider_registry_port import ProviderRegistryPort
from orb.providers.registry import ProviderRegistry

_PROVIDER_ORDER = ["aws", "azure", "gcp", "k8s"]


def scripted_input(provider_type: str, answers: Optional[dict[str, str]] = None) -> Callable:
    """Return an ``input`` replacement that answers prompts by substring match."""
    table = {
        "Select scheduler": "1",
        "Select provider": str(_PROVIDER_ORDER.index(provider_type) + 1),
        **(answers or {}),
    }

    def _input(prompt: str = "") -> str:
        for fragment, answer in table.items():
            if fragment in prompt:
                return answer
        if prompt.strip() == "Select:":
            return "1"
        if "Add another provider" in prompt:
            return "n"
        return ""

    return _input


def run_interactive_init(
    provider_type: str,
    tmp_path: Path,
    answers: Optional[dict[str, str]] = None,
    *,
    force: bool = True,
    console: Optional[MagicMock] = None,
) -> int:
    """Run ``handle_init`` interactively for ``provider_type`` and return its exit code."""
    registry = ProviderRegistry()
    for registered in _PROVIDER_ORDER:
        registry.ensure_provider_type_registered(registered)
    # Azure's lazy registration omits strategy_class (only its plugin sets it).
    azure_registration = registry._get_type_registration("azure")
    if azure_registration.strategy_class is None:
        from orb.providers.azure.strategy.azure_provider_strategy import AzureProviderStrategy

        azure_registration.strategy_class = AzureProviderStrategy
    console = console or MagicMock()
    container = MagicMock()
    container.get.side_effect = lambda port: {
        ProviderRegistryPort: registry,
        ConsolePort: console,
    }.get(port, MagicMock())
    args = argparse.Namespace(
        _container=container,
        config_dir=str(tmp_path / "config"),
        scripts_dir=None,
        force=force,
        non_interactive=False,
    )
    schedulers: list[dict[str, Any]] = [
        {"type": "default", "display_name": "Default", "description": "Default"}
    ]
    with (
        patch.object(init_handler, "_get_available_schedulers", return_value=schedulers),
        patch.object(init_handler, "_create_directories"),
        patch.object(init_handler, "_write_config_file"),
        patch.object(init_handler, "_copy_scripts"),
        patch("builtins.input", scripted_input(provider_type, answers)),
    ):
        return asyncio.run(init_handler.handle_init(args))


def run_cli_init(
    provider_type: str,
    tmp_path: Path,
    answers: Optional[dict[str, str]] = None,
) -> tuple[int, dict[str, Any]]:
    """Run ``orb init`` through the real CLI entry point and return ``(exit code, config.json)``.

    Prompts are answered from a script; nothing is stubbed in the handler, the
    container or the file writers, so the configuration lands on disk exactly as
    for a user.  The returned dict is empty when no ``config.json`` was written.
    """
    import json
    import os
    import sys

    from orb.cli.main import main
    from orb.infrastructure.di.container import reset_container

    config_file = tmp_path / "config" / "config.json"
    argv = ["orb", "init", "--force", "--config-dir", str(config_file.parent)]
    isolated_env = {
        "ORB_LOG_CONSOLE_ENABLED": "false",
        "ORB_ROOT_DIR": str(tmp_path),
        "ORB_CONFIG_DIR": str(config_file.parent),
        "ORB_WORK_DIR": str(tmp_path / "work"),
        "ORB_LOG_DIR": str(tmp_path / "logs"),
        "ORB_HEALTH_DIR": str(tmp_path / "health"),
    }
    reset_container()
    code = 0
    try:
        with (
            patch.dict(os.environ, isolated_env),
            patch.object(sys, "argv", argv),
            patch("builtins.input", scripted_input(provider_type, answers)),
        ):
            try:
                asyncio.run(main())
            except SystemExit as exit_:
                code = exit_.code if isinstance(exit_.code, int) else 1
    finally:
        reset_container()
    return code, json.loads(config_file.read_text()) if config_file.exists() else {}
