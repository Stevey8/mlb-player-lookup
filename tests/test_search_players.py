"""
Unit tests for web.search_players, covering its three branches:

- a digit query dispatches to lookup_player_by_id
- a name query dispatches to lookup_players_by_name
- a name with multiple MLB matches comes back as multiple results
  (disambiguation) rather than being collapsed to one
- empty queries and name queries with zero matches

All MLB Stats API calls are mocked: web._get_json is monkeypatched with a
fake that never touches the network, so these tests run offline and don't
depend on the live MLB Stats API or any particular player's current stats.
"""

from __future__ import annotations

import pytest

import web


def make_person(player_id: int, full_name: str, team_name: str = "Los Angeles Dodgers") -> dict:
    """Build a minimal MLB Stats API "person" payload, shaped like the real API."""

    return {
        "id": player_id,
        "fullName": full_name,
        "primaryNumber": "17",
        "currentTeam": {"id": 119, "name": team_name},
        "primaryPosition": {
            "code": "3",
            "name": "First Base",
            "type": "Infielder",
            "abbreviation": "1B",
        },
        "batSide": {"code": "L", "description": "Left"},
        "pitchHand": {"code": "R", "description": "Right"},
    }


def fake_get_json(responses: dict[str, dict]):
    """Return a fake _get_json that routes by substring of the requested URL."""

    def _fake(url: str, params: dict | None = None) -> dict:
        for path, payload in responses.items():
            if path in url:
                return payload
        raise AssertionError(f"Unexpected URL in test: {url}")

    return _fake


def test_search_by_id_returns_single_player(monkeypatch):
    person = make_person(660271, "Shohei Ohtani")
    monkeypatch.setattr(
        web, "_get_json", fake_get_json({"/people/660271": {"people": [person]}})
    )

    results = web.search_players("660271")

    assert len(results) == 1
    assert results[0]["mlbam_id"] == 660271
    assert results[0]["full_name"] == "Shohei Ohtani"


def test_search_by_name_single_match(monkeypatch):
    person = make_person(660271, "Shohei Ohtani")
    monkeypatch.setattr(
        web, "_get_json", fake_get_json({"/people/search": {"people": [person]}})
    )

    results = web.search_players("Shohei Ohtani")

    assert len(results) == 1
    assert results[0]["full_name"] == "Shohei Ohtani"


def test_search_by_name_multiple_matches_returns_all_for_disambiguation(monkeypatch):
    # Mirrors the ambiguous-name example already called out in the README.
    muncy_a = make_person(571970, "Max Muncy", team_name="Los Angeles Dodgers")
    muncy_b = make_person(650859, "Max Muncy", team_name="Oakland Athletics")
    monkeypatch.setattr(
        web,
        "_get_json",
        fake_get_json({"/people/search": {"people": [muncy_a, muncy_b]}}),
    )

    results = web.search_players("Max Muncy")

    assert len(results) == 2
    returned_ids = {player["mlbam_id"] for player in results}
    assert returned_ids == {571970, 650859}


@pytest.mark.parametrize("query", ["", "   "])
def test_search_with_empty_query_raises_value_error(query, monkeypatch):
    def _unexpected_call(*args, **kwargs):
        raise AssertionError("Empty query should never reach the MLB Stats API")

    monkeypatch.setattr(web, "_get_json", _unexpected_call)

    with pytest.raises(ValueError):
        web.search_players(query)


def test_search_by_name_with_no_matches_returns_empty_list(monkeypatch):
    monkeypatch.setattr(
        web, "_get_json", fake_get_json({"/people/search": {"people": []}})
    )

    results = web.search_players("Zzzznonexistentplayer")

    assert results == []
