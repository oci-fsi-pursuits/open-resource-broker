"""AWS Session Factory - Centralized boto3 session creation."""

import threading
from typing import Any, Optional

import boto3

from orb.providers.aws.utilities.boto_config import get_boto3_config

# Default timeout config for one-off clients created outside of AWSClient
_DEFAULT_CONFIG = get_boto3_config()

# Init-scoped caches keyed by profile name (``None`` = default credential chain).
# Only successful results are stored; they are dropped by ``clear_shared_sessions``
# when the init run ends.
_shared_lock = threading.Lock()
_shared_sessions: dict[Optional[str], boto3.Session] = {}
_shared_identities: dict[Optional[str], dict[str, Any]] = {}


def get_shared_session(profile: Optional[str] = None) -> boto3.Session:
    """Return the cached session for ``profile``, creating it on first use."""
    profile = profile or None
    with _shared_lock:
        session = _shared_sessions.get(profile)
        if session is None:
            session = boto3.Session(profile_name=profile) if profile else boto3.Session()
            _shared_sessions[profile] = session
        return session


def get_caller_identity(profile: Optional[str] = None) -> dict[str, Any]:
    """Return the cached STS caller identity for ``profile``, resolving it on first use.

    Lookup failures propagate and are not cached, so the next caller retries.
    """
    profile = profile or None
    with _shared_lock:
        identity = _shared_identities.get(profile)
    if identity is not None:
        return identity
    session = get_shared_session(profile)
    identity = session.client("sts", config=_DEFAULT_CONFIG).get_caller_identity()
    with _shared_lock:
        _shared_identities[profile] = identity
    return identity


def clear_shared_sessions() -> None:
    """Drop every cached session and identity."""
    with _shared_lock:
        _shared_sessions.clear()
        _shared_identities.clear()


class AWSSessionFactory:
    """Factory for creating AWS sessions with credential chain fallback."""

    @staticmethod
    def create_session(
        profile: Optional[str] = None,
        region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
    ) -> boto3.Session:
        """Create AWS session with credential chain fallback.

        When explicit key credentials are supplied they are passed directly to
        boto3.Session so the operator-configured keys are used instead of the
        ambient credential chain.  When they are absent (None) boto3 falls back
        to its normal chain (env vars, ~/.aws/credentials, instance profile,
        etc.).  Empty strings are treated as absent — never pass them to boto3
        because boto3 treats "" as a non-None credential and the call will fail
        or use an unexpected identity.

        Args:
            profile: AWS profile name (optional)
            region: AWS region (optional)
            aws_access_key_id: Explicit access key ID (plain str, optional)
            aws_secret_access_key: Explicit secret access key (plain str, optional)
            aws_session_token: Explicit session token (plain str, optional)

        Returns:
            Configured boto3 session
        """
        # Build kwargs dict; only include credential keys when they have a
        # non-empty value so boto3 credential-chain fallback is unaffected.
        kwargs: dict = {}
        if region:
            kwargs["region_name"] = region
        if profile:
            kwargs["profile_name"] = profile
        if aws_access_key_id:
            kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            kwargs["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            kwargs["aws_session_token"] = aws_session_token
        return boto3.Session(**kwargs)

    @staticmethod
    def discover_credentials(profile: Optional[str] = None, region: Optional[str] = None) -> dict:
        """Discover AWS credentials and return metadata.

        Args:
            profile: AWS profile name (optional)
            region: AWS region (optional)

        Returns:
            Dict with success status and credential metadata
        """
        try:
            if region:
                session = AWSSessionFactory.create_session(profile, region)
                identity = session.client("sts", config=_DEFAULT_CONFIG).get_caller_identity()
            else:
                identity = get_caller_identity(profile)
                session = get_shared_session(profile)
            return {
                "success": True,
                "profile": profile,
                "region": session.region_name,
                "account": identity["Account"],
                "identity": identity["Arn"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
