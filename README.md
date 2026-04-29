# mlb-player-lookup

## Local web lookup

Run the browser interface:

```bash
python3 web_player_lookup.py
```

Then open:

```text
http://127.0.0.1:8000
```

The page accepts either a player name or an MLBAM ID in the same search box.
Name searches can return multiple matching players, and each result includes a
headshot, the short lookup fields, and a per-player "Show details" section.
