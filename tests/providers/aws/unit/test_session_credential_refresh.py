"""The shared AWS session keeps authenticating after its credentials expire.

A profile backed by ``credential_process`` hands out short-lived credentials.
The session cached for an ``orb init`` run must re-run the process once those
credentials lapse instead of freezing the first ones it saw.  The credential
process is a real subprocess; only botocore's clock is replaced so the tests
neither sleep nor depend on wall-clock timing.
"""

from __future__ import annotations

import datetime
import shlex
import sys
from pathlib import Path

import pytest
from botocore.exceptions import CredentialRetrievalError
from moto import mock_aws

from orb.providers.aws.session_factory import (
    _shared_identities,
    _shared_sessions,
    get_caller_identity,
    get_shared_session,
)

_PROFILE = "rotating"
_LIFETIME_SECONDS = 3600

_CREDENTIAL_SCRIPT = """\
import datetime
import json
import sys
from pathlib import Path

state = Path(sys.argv[1])
if (state / "fail").exists():
    sys.stderr.write("credential helper unavailable")
    sys.exit(1)
counter = state / "counter"
count = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(count))
offset = int((state / "offset").read_text()) if (state / "offset").exists() else 0
expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
    seconds=offset + {lifetime}
)
print(
    json.dumps(
        {{
            "Version": 1,
            "AccessKeyId": f"key-{{count}}",
            "SecretAccessKey": f"secret-{{count}}",
            "SessionToken": f"token-{{count}}",
            "Expiration": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }}
    )
)
"""


class _Clock:
    """Callable standing in for botocore's ``_local_now`` time fetcher."""

    def __init__(self) -> None:
        self.offset = datetime.timedelta()

    def __call__(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc) + self.offset


class _CredentialProcess:
    def __init__(self, state: Path) -> None:
        self.state = state

    @property
    def runs(self) -> int:
        counter = self.state / "counter"
        return int(counter.read_text()) if counter.exists() else 0

    def advance(self, clock: _Clock, seconds: int) -> None:
        """Move the clock forward; the process issues expiries on the same timeline."""
        clock.offset += datetime.timedelta(seconds=seconds)
        (self.state / "offset").write_text(str(int(clock.offset.total_seconds())))

    def fail(self, failing: bool) -> None:
        marker = self.state / "fail"
        if failing:
            marker.write_text("1")
        else:
            marker.unlink(missing_ok=True)


@pytest.fixture
def credential_process(tmp_path, monkeypatch) -> _CredentialProcess:
    state = tmp_path / "state"
    state.mkdir()
    script = tmp_path / "credential_process.py"
    script.write_text(_CREDENTIAL_SCRIPT.format(lifetime=_LIFETIME_SECONDS))
    command = " ".join(shlex.quote(part) for part in (sys.executable, str(script), str(state)))
    config = tmp_path / "aws_config"
    config.write_text(f"[profile {_PROFILE}]\ncredential_process = {command}\nregion = eu-west-2\n")
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_DEFAULT_PROFILE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "no_credentials"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    return _CredentialProcess(state)


def test_shared_session_reruns_the_credential_process_after_expiry(credential_process) -> None:
    clock = _Clock()
    session = get_shared_session(_PROFILE)
    credentials = session.get_credentials()
    credentials._time_fetcher = clock

    before = credentials.get_frozen_credentials()
    assert credentials.get_frozen_credentials() == before
    assert credential_process.runs == 1

    credential_process.advance(clock, 2 * _LIFETIME_SECONDS)
    after = credentials.get_frozen_credentials()

    assert before.access_key == "key-1"
    assert after.access_key == "key-2"
    assert after.secret_key == "secret-2"
    assert after.token == "token-2"
    assert credential_process.runs == 2
    assert get_shared_session(_PROFILE) is session
    assert session.get_credentials() is credentials


def test_credentials_are_not_refreshed_while_still_valid(credential_process) -> None:
    clock = _Clock()
    credentials = get_shared_session(_PROFILE).get_credentials()
    credentials._time_fetcher = clock

    credential_process.advance(clock, _LIFETIME_SECONDS // 2)

    assert credentials.get_frozen_credentials().access_key == "key-1"
    assert credential_process.runs == 1


def test_failing_credential_process_surfaces_and_is_not_cached(credential_process) -> None:
    credential_process.fail(True)

    with mock_aws():
        with pytest.raises(CredentialRetrievalError):
            get_caller_identity(_PROFILE)
        assert _PROFILE not in _shared_identities
        assert credential_process.runs == 0

        credential_process.fail(False)
        identity = get_caller_identity(_PROFILE)

    assert identity["Account"]
    assert credential_process.runs == 1
    assert _shared_identities[_PROFILE] is identity
    assert _shared_sessions[_PROFILE].get_credentials().get_frozen_credentials().access_key == (
        "key-1"
    )
