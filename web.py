"""
Local web interface for MLB player lookup.

Run:
    python3 web_player_lookup.py

Then open:
    http://localhost:8000
"""

from __future__ import annotations

import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

from lookup import build_photo_url


HOST = "127.0.0.1"
PORT = 8000
MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"
REQUEST_TIMEOUT_SECONDS = 15

PEOPLE_FIELDS = ",".join(
    [
        "people",
        "id",
        "fullName",
        "firstName",
        "lastName",
        "primaryNumber",
        "birthDate",
        "currentAge",
        "birthCity",
        "birthStateProvince",
        "birthCountry",
        "height",
        "weight",
        "active",
        "currentTeam",
        "name",
        "primaryPosition",
        "code",
        "type",
        "abbreviation",
        "useName",
        "useLastName",
        "boxscoreName",
        "nickName",
        "mlbDebutDate",
        "batSide",
        "description",
        "pitchHand",
        "nameSlug",
        "strikeZoneTop",
        "strikeZoneBottom",
    ]
)


class PlayerLookupError(RuntimeError):
    """Raised when a player lookup request fails."""


def search_players(query: str) -> list[dict[str, Any]]:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Search by player name or MLBAM ID.")

    if cleaned_query.isdigit():
        return [lookup_player_by_id(cleaned_query)]

    return lookup_players_by_name(cleaned_query)


def lookup_player_by_id(player_id: int | str) -> dict[str, Any]:
    data = _get_json(
        f"{MLB_API_BASE_URL}/people/{int(player_id)}",
        params={"hydrate": "currentTeam", "fields": PEOPLE_FIELDS},
    )
    people = data.get("people", [])
    if not people:
        raise PlayerLookupError(f"No player found for id={player_id}")
    return _build_player_response(people[0])


def lookup_players_by_name(name: str) -> list[dict[str, Any]]:
    data = _get_json(
        f"{MLB_API_BASE_URL}/people/search",
        params={
            "names": name,
            "hydrate": "currentTeam",
            "fields": PEOPLE_FIELDS,
        },
    )
    return [_build_player_response(player) for player in data.get("people", [])]


def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
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


def _build_player_response(player: dict[str, Any]) -> dict[str, Any]:
    details = _normalize_full_player(player)
    brief = {
        "mlbam_id": details.get("mlbam_id"),
        "full_name": details.get("full_name"),
        "primary_number": details.get("primary_number"),
        "current_team": details.get("current_team_name"),
        "primary_position": details.get("primary_position_name"),
        "bats": details.get("bats"),
        "throws": details.get("throws"),
    }
    return {
        "mlbam_id": details.get("mlbam_id"),
        "full_name": details.get("full_name"),
        "photo_url": details.get("photo_url"),
        "brief": brief,
        "details": details,
    }


def _normalize_full_player(player: dict[str, Any]) -> dict[str, Any]:
    player_id = player.get("id")
    primary_position = player.get("primaryPosition") or {}
    current_team = player.get("currentTeam") or {}
    bat_side = player.get("batSide") or {}
    pitch_hand = player.get("pitchHand") or {}

    return {
        "mlbam_id": player_id,
        "full_name": player.get("fullName"),
        "first_name": player.get("firstName"),
        "last_name": player.get("lastName"),
        "primary_number": player.get("primaryNumber"),
        "birth_date": player.get("birthDate"),
        "age": _calculate_age(player.get("birthDate")) or player.get("currentAge"),
        "birth_city": player.get("birthCity"),
        "birth_state_province": player.get("birthStateProvince"),
        "birth_country": player.get("birthCountry"),
        "height": player.get("height"),
        "weight": player.get("weight"),
        "active": player.get("active"),
        "current_team_id": current_team.get("id"),
        "current_team_name": current_team.get("name"),
        "primary_position_code": primary_position.get("code"),
        "primary_position_name": primary_position.get("name"),
        "primary_position_type": primary_position.get("type"),
        "primary_position_abbreviation": primary_position.get("abbreviation"),
        "player_type": _classify_player_type(primary_position),
        "bats": bat_side.get("code"),
        "bats_description": bat_side.get("description"),
        "throws": pitch_hand.get("code"),
        "throws_description": pitch_hand.get("description"),
        "mlb_debut_date": player.get("mlbDebutDate"),
        "name_slug": player.get("nameSlug"),
        "nick_name": player.get("nickName"),
        "strike_zone_top": player.get("strikeZoneTop"),
        "strike_zone_bottom": player.get("strikeZoneBottom"),
        "photo_url": build_photo_url(player_id) if player_id else None,
    }


def _classify_player_type(primary_position: dict[str, Any]) -> str | None:
    code = primary_position.get("code")
    name = primary_position.get("name")
    position_type = primary_position.get("type")

    if code == "Y" or name == "Two-Way Player" or position_type == "Two-Way Player":
        return "two_way"
    if position_type == "Pitcher" or name == "Pitcher":
        return "pitcher"
    if primary_position:
        return "position_player"
    return None


def _calculate_age(birth_date: str | None, today: date | None = None) -> int | None:
    if not birth_date:
        return None

    today = today or date.today()
    born = date.fromisoformat(birth_date)
    birthday_passed = (today.month, today.day) >= (born.month, born.day)
    return today.year - born.year - (0 if birthday_passed else 1)


class PlayerLookupHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/":
            self._send_html(INDEX_HTML)
            return

        if parsed_url.path == "/api/players":
            params = parse_qs(parsed_url.query)
            query = params.get("query", [""])[0]
            self._handle_search(query)
            return

        self._send_json({"error": "Not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_search(self, query: str) -> None:
        try:
            players = search_players(query)
        except (PlayerLookupError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        self._send_json({"query": query, "count": len(players), "players": players})

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MLB Player Lookup</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f7fb;
      --panel: #ffffff;
      --text: #18202d;
      --muted: #657085;
      --line: #d9e1ec;
      --accent: #0f6b5f;
      --accent-dark: #0b4f47;
      --gold: #c8912c;
      --danger: #9f2f2f;
      --shadow: 0 18px 45px rgba(33, 45, 67, 0.12);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(180deg, rgba(15, 107, 95, 0.10), transparent 310px),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    main {
      width: min(1080px, calc(100% - 32px));
      margin: 0 auto;
      padding: 34px 0 56px;
    }

    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 22px;
    }

    h1 {
      margin: 0;
      font-size: clamp(2rem, 5vw, 4.4rem);
      line-height: 0.94;
      letter-spacing: 0;
    }

    .subtitle {
      max-width: 470px;
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.5;
    }

    .status-pill {
      flex: 0 0 auto;
      border: 1px solid rgba(15, 107, 95, 0.24);
      color: var(--accent-dark);
      background: rgba(255, 255, 255, 0.74);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 0.84rem;
      font-weight: 700;
    }

    .search-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 16px;
      margin-bottom: 22px;
    }

    form {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
    }

    label {
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    input {
      width: 100%;
      min-height: 48px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 14px;
      color: var(--text);
      font: inherit;
      font-size: 1rem;
      outline: none;
    }

    input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(15, 107, 95, 0.14);
    }

    button {
      align-self: end;
      min-height: 48px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      padding: 0 22px;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }

    button:hover {
      background: var(--accent-dark);
    }

    button:disabled {
      cursor: wait;
      opacity: 0.72;
    }

    .message {
      display: none;
      margin: 12px 0 0;
      color: var(--muted);
      line-height: 1.45;
    }

    .message.is-visible {
      display: block;
    }

    .message.is-error {
      color: var(--danger);
    }

    .results {
      display: grid;
      gap: 16px;
    }

    .player {
      display: grid;
      grid-template-columns: 190px 1fr;
      gap: 18px;
      align-items: start;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(33, 45, 67, 0.08);
      padding: 16px;
    }

    .headshot-wrap {
      aspect-ratio: 1 / 1;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #eef3f7;
      overflow: hidden;
    }

    .headshot {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .player h2 {
      margin: 0 0 8px;
      font-size: clamp(1.45rem, 3vw, 2.2rem);
      line-height: 1.05;
      letter-spacing: 0;
    }

    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }

    .chip {
      border: 1px solid rgba(200, 145, 44, 0.34);
      background: rgba(200, 145, 44, 0.10);
      color: #6b4a13;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 0.82rem;
      font-weight: 800;
    }

    .brief-grid,
    .details-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .field {
      min-width: 0;
      border-top: 1px solid var(--line);
      padding-top: 9px;
    }

    .field-label {
      color: var(--muted);
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .field-value {
      margin-top: 3px;
      overflow-wrap: anywhere;
      font-weight: 720;
    }

    details {
      margin-top: 14px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }

    summary {
      color: var(--accent-dark);
      cursor: pointer;
      font-weight: 900;
    }

    .details-grid {
      margin-top: 12px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    @media (max-width: 760px) {
      main {
        width: min(100% - 22px, 1080px);
        padding-top: 22px;
      }

      header {
        display: block;
      }

      .status-pill {
        display: inline-block;
        margin-top: 16px;
      }

      form,
      .player,
      .brief-grid,
      .details-grid {
        grid-template-columns: 1fr;
      }

      button {
        width: 100%;
      }

      .headshot-wrap {
        max-width: 260px;
      }
    }
  </style>

  <script defer data-domain="mlb-player-lookup.onrender.com" src="https://plausible.io/js/script.js"></script>

</head>
<body>
  <main>
    <header>
      <div>
        <h1>MLB Player Lookup</h1>
        <p class="subtitle">Search one box by MLBAM ID or player name. Shared names return every matching profile with photos and per-player details.</p>
      </div>
    </header>

    <section class="search-panel" aria-label="Player search">
      <form id="search-form">
        <div>
          <label for="query">Name or MLBAM ID</label>
          <input id="query" name="query" type="search" placeholder="Shohei Ohtani or 660271" autocomplete="off" autofocus>
        </div>
        <button id="search-button" type="submit">Search</button>
      </form>
      <p id="message" class="message"></p>
    </section>

    <section id="results" class="results" aria-live="polite"></section>
  </main>

  <template id="player-template">
    <article class="player">
      <div class="headshot-wrap">
        <img class="headshot" alt="">
      </div>
      <div>
        <h2></h2>
        <div class="meta"></div>
        <div class="brief-grid"></div>
        <details>
          <summary>Show details</summary>
          <div class="details-grid"></div>
        </details>
      </div>
    </article>
  </template>

  <script>
    const form = document.querySelector("#search-form");
    const input = document.querySelector("#query");
    const button = document.querySelector("#search-button");
    const message = document.querySelector("#message");
    const results = document.querySelector("#results");
    const template = document.querySelector("#player-template");

    const briefOrder = [
      ["mlbam_id", "MLBAM ID"],
      ["full_name", "Full name"],
      ["primary_number", "Primary number"],
      ["current_team", "Current team"],
      ["primary_position", "Primary position"],
      ["bats", "Bats"],
      ["throws", "Throws"],
    ];

    const detailLabels = {
      mlbam_id: "MLBAM ID",
      full_name: "Full name",
      first_name: "First name",
      last_name: "Last name",
      primary_number: "Primary number",
      birth_date: "Birth date",
      age: "Age",
      birth_city: "Birth city",
      birth_state_province: "Birth state/province",
      birth_country: "Birth country",
      height: "Height",
      weight: "Weight",
      active: "Active",
      current_team_id: "Current team ID",
      current_team_name: "Current team",
      primary_position_code: "Position code",
      primary_position_name: "Position",
      primary_position_type: "Position type",
      primary_position_abbreviation: "Position abbreviation",
      player_type: "Player type",
      bats: "Bats",
      bats_description: "Bats description",
      throws: "Throws",
      throws_description: "Throws description",
      mlb_debut_date: "MLB debut date",
      name_slug: "Name slug",
      nick_name: "Nickname",
      strike_zone_top: "Strike zone top",
      strike_zone_bottom: "Strike zone bottom",
      photo_url: "Photo URL",
    };

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const query = input.value.trim();
      if (!query) {
        showMessage("Search by player name or MLBAM ID.", true);
        input.focus();
        return;
      }

      setLoading(true);
      showMessage("Searching MLB Stats API...", false);
      results.replaceChildren();

      try {
        const response = await fetch(`/api/players?query=${encodeURIComponent(query)}`);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || "Lookup failed.");
        }

        if (payload.players.length === 0) {
          showMessage(`No players found for "${query}".`, false);
          return;
        }

        renderPlayers(payload.players);
        showMessage(`${payload.players.length} result${payload.players.length === 1 ? "" : "s"} found.`, false);
      } catch (error) {
        showMessage(error.message, true);
      } finally {
        setLoading(false);
      }
    });

    function setLoading(isLoading) {
      button.disabled = isLoading;
      button.textContent = isLoading ? "Searching" : "Search";
    }

    function showMessage(text, isError) {
      message.textContent = text;
      message.classList.toggle("is-error", isError);
      message.classList.toggle("is-visible", Boolean(text));
    }

    function renderPlayers(players) {
      const fragment = document.createDocumentFragment();
      players.forEach((player, index) => {
        const node = template.content.cloneNode(true);
        const article = node.querySelector(".player");
        const image = node.querySelector(".headshot");
        const title = node.querySelector("h2");
        const meta = node.querySelector(".meta");
        const briefGrid = node.querySelector(".brief-grid");
        const detailsGrid = node.querySelector(".details-grid");

        article.setAttribute("aria-label", player.full_name || `Player ${index + 1}`);
        image.src = player.photo_url;
        image.alt = `${player.full_name || "Player"} headshot`;
        title.textContent = player.full_name || `Player ${index + 1}`;

        addChip(meta, `Result ${index + 1}`);
        if (player.brief.current_team) addChip(meta, player.brief.current_team);
        if (player.brief.primary_position) addChip(meta, player.brief.primary_position);

        briefOrder.forEach(([key, label]) => {
          addField(briefGrid, label, player.brief[key]);
        });

        Object.keys(detailLabels).forEach((key) => {
          addField(detailsGrid, detailLabels[key], player.details[key]);
        });

        fragment.appendChild(node);
      });
      results.replaceChildren(fragment);
    }

    function addChip(parent, text) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = text;
      parent.appendChild(chip);
    }

    function addField(parent, label, value) {
      const wrapper = document.createElement("div");
      wrapper.className = "field";

      const labelEl = document.createElement("div");
      labelEl.className = "field-label";
      labelEl.textContent = label;

      const valueEl = document.createElement("div");
      valueEl.className = "field-value";
      valueEl.textContent = formatValue(value);

      wrapper.append(labelEl, valueEl);
      parent.appendChild(wrapper);
    }

    function formatValue(value) {
      if (value === null || value === undefined || value === "") return "N/A";
      if (typeof value === "boolean") return value ? "Yes" : "No";
      return String(value);
    }
  </script>
</body>
</html>
"""


def main() -> None:
    import os

    host = "0.0.0.0" if "PORT" in os.environ else HOST
    port = int(os.environ.get("PORT", PORT))

    server = ThreadingHTTPServer((host, port), PlayerLookupHandler)
    print(f"MLB Player Lookup running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
