"""
Integration test for the /api/players HTTP endpoint.

Starts web.PlayerLookupHandler on a real socket bound to an OS-assigned free
port (port 0), with web._get_json monkeypatched so the request never leaves
the machine, then makes a real HTTP request against it and checks the JSON
shape the frontend (and any API consumer) relies on.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import web


def _fake_get_json(url: str, params: dict | None = None) -> dict:
    person = {
        "id": 660271,
        "fullName": "Shohei Ohtani",
        "primaryNumber": "17",
        "currentTeam": {"id": 119, "name": "Los Angeles Dodgers"},
        "primaryPosition": {
            "code": "Y",
            "name": "Two-Way Player",
            "type": "Two-Way Player",
            "abbreviation": "TWP",
        },
        "batSide": {"code": "L", "description": "Left"},
        "pitchHand": {"code": "R", "description": "Right"},
    }
    return {"people": [person]}


@pytest.fixture
def live_server(monkeypatch):
    monkeypatch.setattr(web, "_get_json", _fake_get_json)

    server = ThreadingHTTPServer(("127.0.0.1", 0), web.PlayerLookupHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_api_players_returns_expected_json_shape(live_server):
    with urllib.request.urlopen(f"{live_server}/api/players?query=660271", timeout=5) as response:
        assert response.status == 200
        assert response.headers.get("Content-Type", "").startswith("application/json")
        payload = json.load(response)

    assert payload["query"] == "660271"
    assert payload["count"] == 1
    assert len(payload["players"]) == 1

    player = payload["players"][0]
    assert player["mlbam_id"] == 660271
    assert player["full_name"] == "Shohei Ohtani"
    assert player["photo_url"].startswith("https://img.mlbstatic.com/")

    assert set(player["brief"]) == {
        "mlbam_id",
        "full_name",
        "primary_number",
        "current_team",
        "primary_position",
        "bats",
        "throws",
    }
    assert player["brief"]["current_team"] == "Los Angeles Dodgers"
    assert player["details"]["current_team_name"] == "Los Angeles Dodgers"


def test_api_players_with_empty_query_returns_400(live_server):
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{live_server}/api/players?query=", timeout=5)

    assert exc_info.value.code == 400
    payload = json.load(exc_info.value)
    assert "error" in payload
