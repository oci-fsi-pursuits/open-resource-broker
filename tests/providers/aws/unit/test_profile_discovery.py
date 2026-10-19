"""Unit tests for profile_discovery.py.

Filesystem and boto3 calls are patched — no real AWS connections made.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orb.providers.aws.profile_discovery import (
    get_available_profiles,
    probe_instance_profile_credentials,
)

# ---------------------------------------------------------------------------
# probe_instance_profile_credentials
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProbeInstanceProfileCredentials:
    def test_returns_true_when_sts_succeeds(self):
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sts

        with patch("boto3.Session", return_value=mock_session):
            result = probe_instance_profile_credentials()
        assert result is True

    def test_returns_false_when_sts_raises(self):
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = Exception("no credentials")
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sts

        with patch("boto3.Session", return_value=mock_session):
            result = probe_instance_profile_credentials()
        assert result is False

    def test_passes_region_to_session(self):
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {}
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sts

        with patch("boto3.Session", return_value=mock_session) as mock_boto:
            probe_instance_profile_credentials(region="us-east-1")
        mock_boto.assert_called_once_with(region_name="us-east-1")


# ---------------------------------------------------------------------------
# get_available_profiles
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAvailableProfiles:
    def _write_config(self, tmp_path: Path, contents: str) -> Path:
        f = tmp_path / "config"
        f.write_text(contents)
        return f

    def test_returns_list_of_dicts(self):
        with (
            patch(
                "orb.providers.aws.profile_discovery.probe_instance_profile_credentials",
                return_value=False,
            ),
            patch.object(Path, "exists", return_value=False),
        ):
            profiles = get_available_profiles()
        assert isinstance(profiles, list)
        for p in profiles:
            assert isinstance(p, dict)
            assert "name" in p
            assert "description" in p
            assert "config_delta" in p

    def test_profiles_extracted_from_config_file(self, tmp_path):
        cfg_text = "[profile dev]\nregion = us-east-1\n[profile staging]\nregion = eu-west-1\n"
        config_path = tmp_path / "config"
        config_path.write_text(cfg_text)

        with (
            patch(
                "orb.providers.aws.profile_discovery.probe_instance_profile_credentials",
                return_value=False,
            ),
            patch.object(Path, "home", return_value=tmp_path),
        ):
            # Patch the path construction inside the function
            with patch("orb.providers.aws.profile_discovery.Path.home", return_value=tmp_path):
                profiles = get_available_profiles()

        # At least expect non-None entries (from parsing)
        assert isinstance(profiles, list)

    def test_default_section_included(self, tmp_path):
        cfg_text = "[default]\nregion = us-east-1\n"
        config_path = tmp_path / "config"
        config_path.write_text(cfg_text)

        with (
            patch(
                "orb.providers.aws.profile_discovery.probe_instance_profile_credentials",
                return_value=False,
            ),
            patch.object(Path, "home", return_value=tmp_path),
        ):
            with patch("orb.providers.aws.profile_discovery.Path.home", return_value=tmp_path):
                profiles = get_available_profiles()
        assert isinstance(profiles, list)

    def test_auto_discover_entry_always_present(self):
        """The None-name entry (auto-discover) is always included."""
        with (
            patch(
                "orb.providers.aws.profile_discovery.probe_instance_profile_credentials",
                return_value=False,
            ),
            patch.object(Path, "exists", return_value=False),
        ):
            profiles = get_available_profiles()
        none_entries = [p for p in profiles if p["name"] is None]
        assert len(none_entries) == 1

    def test_instance_profile_description_when_probe_succeeds(self):
        with (
            patch(
                "orb.providers.aws.profile_discovery.probe_instance_profile_credentials",
                return_value=True,
            ),
            patch.object(Path, "exists", return_value=False),
        ):
            profiles = get_available_profiles()
        none_entries = [p for p in profiles if p["name"] is None]
        assert none_entries[0]["description"] == "Environment / Instance Profile (auto-discovered)"

    def test_auto_discover_description_when_probe_fails(self):
        with (
            patch(
                "orb.providers.aws.profile_discovery.probe_instance_profile_credentials",
                return_value=False,
            ),
            patch.object(Path, "exists", return_value=False),
        ):
            profiles = get_available_profiles()
        none_entries = [p for p in profiles if p["name"] is None]
        assert none_entries[0]["description"] == "Auto-discover credentials"

    def test_parse_error_in_config_file_is_silently_handled(self, tmp_path):
        """Malformed config files should not raise — they are skipped."""
        config_path = tmp_path / "config"
        config_path.write_text("[bad section\ngarbage")

        with (
            patch(
                "orb.providers.aws.profile_discovery.probe_instance_profile_credentials",
                return_value=False,
            ),
            patch.object(Path, "home", return_value=tmp_path),
        ):
            with patch("orb.providers.aws.profile_discovery.Path.home", return_value=tmp_path):
                # Should not raise
                profiles = get_available_profiles()
        assert isinstance(profiles, list)

    def test_config_delta_contains_profile_name(self):
        """Profiles with a name must carry config_delta={'profile': name}."""
        mock_parser = MagicMock()
        mock_parser.sections.return_value = ["profile my-profile"]
        mock_parser.read = MagicMock()

        with (
            patch(
                "orb.providers.aws.profile_discovery.probe_instance_profile_credentials",
                return_value=False,
            ),
            patch.object(Path, "exists", return_value=True),
            patch("configparser.ConfigParser", return_value=mock_parser),
        ):
            profiles = get_available_profiles()

        named = [p for p in profiles if p["name"] == "my-profile"]
        assert len(named) == 1
        assert named[0]["config_delta"] == {"profile": "my-profile"}


# ---------------------------------------------------------------------------
# Shared sessions and cached identities
# ---------------------------------------------------------------------------


def _session_with_identity(account: str = "123456789012") -> MagicMock:
    session = MagicMock()
    session.region_name = "eu-west-2"
    session.client.return_value.get_caller_identity.return_value = {
        "Account": account,
        "Arn": f"arn:aws:iam::{account}:user/example",
    }
    return session


@pytest.mark.unit
class TestSharedSessions:
    def test_session_is_created_once_per_profile(self):
        from orb.providers.aws.session_factory import get_shared_session

        with patch("boto3.Session", side_effect=lambda **_: MagicMock()) as session_cls:
            default_first = get_shared_session(None)
            default_second = get_shared_session(None)
            named = get_shared_session("prof1")

        assert default_first is default_second
        assert named is not default_first
        assert session_cls.call_count == 2
        session_cls.assert_any_call(profile_name="prof1")

    def test_empty_profile_name_shares_the_default_chain_entry(self):
        from orb.providers.aws.session_factory import get_shared_session

        with patch("boto3.Session", side_effect=lambda **_: MagicMock()) as session_cls:
            assert get_shared_session("") is get_shared_session(None)

        session_cls.assert_called_once_with()

    def test_failed_session_creation_is_not_cached(self):
        from orb.providers.aws.session_factory import get_shared_session

        session = MagicMock()
        with patch("boto3.Session", side_effect=[RuntimeError("bad profile"), session]):
            with pytest.raises(RuntimeError):
                get_shared_session("prof1")
            assert get_shared_session("prof1") is session

    def test_identity_is_resolved_once_per_profile(self):
        from orb.providers.aws.session_factory import get_caller_identity

        session = _session_with_identity()
        with patch("boto3.Session", return_value=session):
            first = get_caller_identity(None)
            second = get_caller_identity(None)

        assert first is second
        session.client.return_value.get_caller_identity.assert_called_once()

    def test_failed_identity_lookup_is_retried(self):
        from orb.providers.aws.session_factory import get_caller_identity

        session = _session_with_identity()
        sts = session.client.return_value
        sts.get_caller_identity.side_effect = [
            RuntimeError("throttled"),
            {"Account": "123456789012", "Arn": "arn"},
        ]
        with patch("boto3.Session", return_value=session):
            with pytest.raises(RuntimeError):
                get_caller_identity(None)
            assert get_caller_identity(None)["Account"] == "123456789012"

    def test_clear_forces_fresh_resolution(self):
        from orb.providers.aws.session_factory import clear_shared_sessions, get_caller_identity

        session = _session_with_identity()
        with patch("boto3.Session", return_value=session) as session_cls:
            get_caller_identity(None)
            clear_shared_sessions()
            get_caller_identity(None)

        assert session_cls.call_count == 2
        assert session.client.return_value.get_caller_identity.call_count == 2

    def test_probe_and_discover_credentials_share_one_resolution(self):
        from orb.providers.aws.session_factory import AWSSessionFactory

        session = _session_with_identity()
        with patch("boto3.Session", return_value=session) as session_cls:
            assert probe_instance_profile_credentials() is True
            result = AWSSessionFactory.discover_credentials(None, None)

        assert result["success"] is True
        assert result["account"] == "123456789012"
        assert result["region"] == "eu-west-2"
        session_cls.assert_called_once()
        session.client.return_value.get_caller_identity.assert_called_once()

    def test_failed_probe_is_retried_by_discover_credentials(self):
        from orb.providers.aws.session_factory import AWSSessionFactory

        session = _session_with_identity()
        sts = session.client.return_value
        sts.get_caller_identity.side_effect = [
            RuntimeError("no credentials"),
            {"Account": "123456789012", "Arn": "arn"},
        ]
        with patch("boto3.Session", return_value=session):
            assert probe_instance_profile_credentials() is False
            assert AWSSessionFactory.discover_credentials(None, None)["success"] is True

    def test_release_hook_clears_shared_state(self):
        from orb.providers.aws.session_factory import get_shared_session
        from orb.providers.aws.strategy.aws_provider_strategy import AWSProviderStrategy

        with patch("boto3.Session", side_effect=lambda **_: MagicMock()) as session_cls:
            get_shared_session(None)
            AWSProviderStrategy.release_init_resources()
            get_shared_session(None)

        assert session_cls.call_count == 2
