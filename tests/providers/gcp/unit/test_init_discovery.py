"""GCP init discovery reads paginated project and region listings."""

from unittest.mock import MagicMock

import pytest

from orb.providers.gcp.services import init_discovery


def test_default_project_uses_adc_scope(monkeypatch) -> None:
    auth_default = MagicMock(return_value=(object(), "selected-project"))
    monkeypatch.setattr("google.auth.default", auth_default)

    assert init_discovery.default_project() == "selected-project"
    auth_default.assert_called_once_with(scopes=["https://www.googleapis.com/auth/cloud-platform"])


def test_project_search_pages_and_closes_session(monkeypatch) -> None:
    session = MagicMock()
    first = MagicMock()
    first.json.return_value = {
        "projects": [{"projectId": "project-b", "displayName": "B", "state": "ACTIVE"}],
        "nextPageToken": "next",
    }
    second = MagicMock()
    second.json.return_value = {
        "projects": [
            {"projectId": "project-a", "displayName": "A", "state": "ACTIVE"},
            {"projectId": "deleted", "state": "DELETE_REQUESTED"},
        ]
    }
    session.get.side_effect = [first, second]
    monkeypatch.setattr("google.auth.default", lambda **_kwargs: (object(), None))
    monkeypatch.setattr(
        "google.auth.transport.requests.AuthorizedSession", MagicMock(return_value=session)
    )

    assert init_discovery.list_projects() == [("project-a", "A"), ("project-b", "B")]
    assert session.get.call_args_list[0].kwargs["params"] is None
    assert session.get.call_args_list[1].kwargs["params"] == {"pageToken": "next"}
    session.close.assert_called_once()


def test_regions_use_selected_project(monkeypatch) -> None:
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {
        "items": [
            {"name": "europe-west2", "status": "UP"},
            {"name": "us-central1", "status": "DOWN"},
        ]
    }
    session.get.return_value = response
    auth_default = MagicMock(return_value=(object(), None))
    monkeypatch.setattr("google.auth.default", auth_default)
    monkeypatch.setattr(
        "google.auth.transport.requests.AuthorizedSession", MagicMock(return_value=session)
    )

    assert init_discovery.list_regions("selected-project") == [("europe-west2", "europe-west2")]
    assert "/projects/selected-project/regions" in session.get.call_args.args[0]
    assert auth_default.call_args.kwargs["scopes"] == [
        "https://www.googleapis.com/auth/cloud-platform"
    ]
    session.close.assert_called_once()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "invalid response"),
        ({"nextPageToken": 42}, "invalid page token"),
        ({"projects": {}}, "invalid projects"),
        ({"projects": [None]}, "invalid project"),
    ],
)
def test_project_discovery_rejects_malformed_api_data_and_closes_session(
    monkeypatch, payload, message
) -> None:
    session = MagicMock()
    session.get.return_value.json.return_value = payload
    monkeypatch.setattr("google.auth.default", lambda **_kwargs: (object(), None))
    monkeypatch.setattr(
        "google.auth.transport.requests.AuthorizedSession", MagicMock(return_value=session)
    )

    with pytest.raises(ValueError, match=message):
        init_discovery.list_projects()

    session.close.assert_called_once()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"items": {}}, "invalid regions"),
        ({"items": [None]}, "invalid region"),
    ],
)
def test_region_discovery_rejects_malformed_api_data(monkeypatch, payload, message) -> None:
    session = MagicMock()
    session.get.return_value.json.return_value = payload
    monkeypatch.setattr("google.auth.default", lambda **_kwargs: (object(), None))
    monkeypatch.setattr(
        "google.auth.transport.requests.AuthorizedSession", MagicMock(return_value=session)
    )

    with pytest.raises(ValueError, match=message):
        init_discovery.list_regions("selected-project")

    session.close.assert_called_once()


def test_project_discovery_uses_project_id_when_display_name_is_missing(monkeypatch) -> None:
    session = MagicMock()
    session.get.return_value.json.return_value = {
        "projects": [{"projectId": "selected-project", "state": "ACTIVE"}]
    }
    monkeypatch.setattr("google.auth.default", lambda **_kwargs: (object(), None))
    monkeypatch.setattr(
        "google.auth.transport.requests.AuthorizedSession", MagicMock(return_value=session)
    )

    assert init_discovery.list_projects() == [("selected-project", "selected-project")]


def test_discovery_page_limit_closes_session(monkeypatch) -> None:
    session = MagicMock()
    session.get.return_value.json.return_value = {"nextPageToken": "same-token"}
    monkeypatch.setattr(init_discovery, "_MAX_DISCOVERY_PAGES", 2)
    monkeypatch.setattr("google.auth.default", lambda **_kwargs: (object(), None))
    monkeypatch.setattr(
        "google.auth.transport.requests.AuthorizedSession", MagicMock(return_value=session)
    )

    with pytest.raises(ValueError, match="page limit"):
        init_discovery.list_projects()

    assert session.get.call_count == 2
    session.close.assert_called_once()


def test_region_request_quotes_free_text_project_id(monkeypatch) -> None:
    session = MagicMock()
    session.get.return_value.json.return_value = {"items": []}
    monkeypatch.setattr("google.auth.default", lambda **_kwargs: (object(), None))
    monkeypatch.setattr(
        "google.auth.transport.requests.AuthorizedSession", MagicMock(return_value=session)
    )

    assert init_discovery.list_regions("a/b?x") == []
    assert "/projects/a%2Fb%3Fx/regions" in session.get.call_args.args[0]


def test_discovery_calls_share_one_adc_resolution(monkeypatch) -> None:
    credentials = object()
    auth_default = MagicMock(return_value=(credentials, "selected-project"))
    monkeypatch.setattr("google.auth.default", auth_default)
    session_cls = MagicMock()
    session_cls.return_value.get.return_value.json.return_value = {"items": [], "projects": []}
    monkeypatch.setattr("google.auth.transport.requests.AuthorizedSession", session_cls)

    assert init_discovery.default_project() == "selected-project"
    init_discovery.list_projects()
    init_discovery.list_regions("selected-project")
    assert init_discovery.default_project() == "selected-project"

    auth_default.assert_called_once_with(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    assert [call.args[0] for call in session_cls.call_args_list] == [credentials, credentials]


def test_failed_adc_resolution_is_not_cached(monkeypatch) -> None:
    auth_default = MagicMock(side_effect=[RuntimeError("ADC unavailable"), (object(), "project")])
    monkeypatch.setattr("google.auth.default", auth_default)

    with pytest.raises(RuntimeError):
        init_discovery.default_project()

    assert init_discovery.default_project() == "project"
    assert auth_default.call_count == 2


def test_clearing_forces_a_fresh_adc_resolution(monkeypatch) -> None:
    auth_default = MagicMock(return_value=(object(), "project"))
    monkeypatch.setattr("google.auth.default", auth_default)

    init_discovery.default_project()
    init_discovery.clear_default_credentials()
    init_discovery.default_project()

    assert auth_default.call_count == 2


def test_release_hook_clears_cached_adc(monkeypatch) -> None:
    from orb.providers.gcp.strategy.gcp_provider_strategy import GCPProviderStrategy

    auth_default = MagicMock(return_value=(object(), "project"))
    monkeypatch.setattr("google.auth.default", auth_default)

    init_discovery.default_project()
    GCPProviderStrategy.release_init_resources()
    init_discovery.default_project()

    assert auth_default.call_count == 2
