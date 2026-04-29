"""
A lightweight MLB Stats API client to look up players by name or MLBAM ID.

Information returned: 
- mlbam_id
- full_name
- primary_number
- current_team
- primary_position
- bats
- throws

To show player headshot, use the `--show-photo` flag. 
This will open the player's MLB headshot URL in the default browser. 
Note that this only works when the lookup resolves to exactly one player.

Example usage:
- `python lookup.py --name "Shohei Ohtani"`
- `python lookup.py --id 660271`
- `python lookup.py --name "Shohei Ohtani" --show-photo`
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"
REQUEST_TIMEOUT_SECONDS = 15

PEOPLE_FIELDS = ",".join(
    [
        "people",
        "id",
        "fullName",
        "primaryNumber",
        "currentTeam",
        "primaryPosition",
        "batSide",
        "pitchHand",
        "name",
        "code",
    ]
)

class PlayerLookupError(RuntimeError):
    """Raised when a player lookup request fails."""


def lookup_player_by_id(player_id: int | str) -> dict[str, Any]:
    """Return a normalized player profile for an MLBAM player ID."""

    data = _get_json(
        f"{MLB_API_BASE_URL}/people/{int(player_id)}",
        params={"hydrate": "currentTeam", "fields": PEOPLE_FIELDS},
    )
    people = data.get("people", [])
    if not people:
        raise PlayerLookupError(f"No player found for id={player_id}")
    return _normalize_player(people[0])


def lookup_player_by_name(name: str) -> list[dict[str, Any]]:
    """
    Return normalized player profiles for a name search.

    MLB may return multiple players for the same or similar name. The caller
    should display all results and let the user disambiguate.
    """

    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("name must not be empty")

    data = _get_json(
        f"{MLB_API_BASE_URL}/people/search",
        params={
            "names": cleaned_name,
            "hydrate": "currentTeam",
            "fields": PEOPLE_FIELDS,
        },
    )
    return [_normalize_player(player) for player in data.get("people", [])]


def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Request JSON from the MLB Stats API with consistent error handling."""

    if params:
        url = f"{url}?{urlencode(params)}"

    request = Request(url, headers={"Accept": "application/json"})

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)
    except HTTPError as exc:
        raise PlayerLookupError(
            f"MLB Stats API request failed with status {exc.code}: {exc.reason}"
        ) from exc
    except URLError as exc:
        raise PlayerLookupError(f"MLB Stats API request failed: {exc.reason}") from exc
    except ValueError as exc:
        raise PlayerLookupError("MLB Stats API returned non-JSON response") from exc


def _normalize_player(player: dict[str, Any]) -> dict[str, Any]:
    """Flatten the MLB player payload into the fields the backend cares about."""

    player_id = player.get("id")
    primary_position = player.get("primaryPosition") or {}
    current_team = player.get("currentTeam") or {}
    bat_side = player.get("batSide") or {}
    pitch_hand = player.get("pitchHand") or {}

    return {
        "mlbam_id": player_id,
        "full_name": player.get("fullName"),
        "primary_number": player.get("primaryNumber"),
        "current_team": current_team.get("name"),
        "primary_position": primary_position.get("name"),
        "bats": bat_side.get("code"),
        "throws": pitch_hand.get("code"),
    }


def build_photo_url(player_id: int | str) -> str:
    """Return MLB's current player headshot URL without adding it to lookup output."""

    safe_player_id = quote(str(player_id), safe="")
    return (
        "https://img.mlbstatic.com/mlb-photos/image/upload/"
        "d_people:generic:headshot:67:current.png/"
        f"w_426,q_auto:best/v1/people/{safe_player_id}/headshot/67/current"
    )


def _open_photo(result: dict[str, Any] | list[dict[str, Any]]) -> None:
    """Open the player photo when the CLI result resolves to one player."""

    if isinstance(result, list):
        if len(result) != 1:
            print(
                f"--show-photo only opens automatically for one result; got {len(result)}.",
                file=sys.stderr,
            )
            return
        player = result[0]
    else:
        player = result

    player_id = player.get("mlbam_id")
    if player_id is None:
        print("No mlbam_id found for this player.", file=sys.stderr)
        return

    webbrowser.open(build_photo_url(player_id))


def main() -> None:
    parser = argparse.ArgumentParser(description="Look up MLB player information.")
    lookup_group = parser.add_mutually_exclusive_group(required=True)
    lookup_group.add_argument("--id", dest="player_id", type=int, help="MLBAM player ID")
    lookup_group.add_argument("--name", help="Player name to search")
    parser.add_argument(
        "--show-photo",
        action="store_true",
        help="Open the player's MLB headshot URL in the default browser",
    )
    args = parser.parse_args()

    if args.player_id is not None:
        result: dict[str, Any] | list[dict[str, Any]] = lookup_player_by_id(args.player_id)
    else:
        result = lookup_player_by_name(args.name)

    print(json.dumps(result, indent=2))
    if args.show_photo:
        _open_photo(result)


if __name__ == "__main__":
    main()
