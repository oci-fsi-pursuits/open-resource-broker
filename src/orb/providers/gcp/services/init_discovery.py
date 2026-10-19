"""Read-only GCP account discovery for the interactive init wizard."""

import threading
from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

_DISCOVERY_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_MAX_DISCOVERY_PAGES = 100

# Application Default Credentials are static for the life of the process, so one
# ``orb init`` run resolves them once.  Only a successful resolution is stored;
# ``clear_default_credentials`` drops it when the run ends so long-running
# processes never hold init-cached credentials.
_adc_lock = threading.Lock()
_adc: tuple[Any, str | None] | None = None


def cached_default_credentials() -> tuple[Any, str | None]:
    """Return ``(credentials, project_id)`` from ADC, resolving them on first use."""
    global _adc
    with _adc_lock:
        if _adc is None:
            import google.auth

            _adc = google.auth.default(scopes=[_DISCOVERY_SCOPE])
        return _adc


def clear_default_credentials() -> None:
    """Forget the cached Application Default Credentials."""
    global _adc
    with _adc_lock:
        _adc = None


def default_project() -> str | None:
    """Return the project selected by Application Default Credentials, if any."""
    _, project_id = cached_default_credentials()
    return project_id


def _list_pages(url: str) -> Iterator[dict[str, Any]]:
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = cached_default_credentials()
    session = AuthorizedSession(credentials)
    try:
        page_token = ""
        for page_number in range(_MAX_DISCOVERY_PAGES):
            response = session.get(url, params={"pageToken": page_token} if page_token else None)
            response.raise_for_status()
            page = response.json()
            if not isinstance(page, dict):
                raise ValueError("GCP discovery returned an invalid response")
            yield page
            page_token = page.get("nextPageToken", "")
            if not isinstance(page_token, str):
                raise ValueError("GCP discovery returned an invalid page token")
            if not page_token:
                break
            if page_number == _MAX_DISCOVERY_PAGES - 1:
                raise ValueError("GCP discovery exceeded the page limit")
    finally:
        session.close()


def list_projects() -> list[tuple[str, str]]:
    """List projects visible to the current identity."""
    projects: dict[str, str] = {}
    for page in _list_pages("https://cloudresourcemanager.googleapis.com/v3/projects:search"):
        entries = page.get("projects", [])
        if not isinstance(entries, list):
            raise ValueError("GCP project discovery returned invalid projects")
        for project in entries:
            if not isinstance(project, dict):
                raise ValueError("GCP project discovery returned an invalid project")
            project_id = project.get("projectId")
            display_name = project.get("displayName")
            if project.get("state") == "ACTIVE" and isinstance(project_id, str) and project_id:
                projects[project_id] = (
                    display_name if isinstance(display_name, str) and display_name else project_id
                )
    return sorted(projects.items())


def list_regions(project_id: str) -> list[tuple[str, str]]:
    """List Compute Engine regions available to the selected project."""
    regions: set[str] = set()
    url = f"https://compute.googleapis.com/compute/v1/projects/{quote(project_id, safe='')}/regions"
    for page in _list_pages(url):
        entries = page.get("items", [])
        if not isinstance(entries, list):
            raise ValueError("GCP region discovery returned invalid regions")
        for region in entries:
            if not isinstance(region, dict):
                raise ValueError("GCP region discovery returned an invalid region")
            region_name = region.get("name")
            if isinstance(region_name, str) and region_name and region.get("status") == "UP":
                regions.add(region_name)
    return [(region, region) for region in sorted(regions)]
