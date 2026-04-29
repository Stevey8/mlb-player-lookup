# MLB Player Lookup

A small MLB player lookup tool for finding player profiles by name or MLBAM
ID. The repo includes a quick terminal script `lookup.py` and a lightweight local web
interface.


## Quick Terminal Lookup

Look up by player name:

```bash
python lookup.py --name "Shohei Ohtani"
```

Look up by MLBAM ID:

```bash
python lookup.py --id 660271
```

To open a player headshot (either `--name` or `--id` works):

```bash
python lookup.py --name "Shohei Ohtani" --show-photo
```

*Note: headshot will only show up if there is only one exact match.*
*For example, `--name "Max Muncy" --show-photo` would not open the player photo because there are multiple Max Muncy.*
*However you can still find the unique id for each Max Muncy, then use that id to look up the headshot.*



## Web Interface

The web app lets you search with one box, using either a player name or an
MLBAM ID. Each result shows a player headshot, a short lookup summary, and a
per-player "Show details" section for the full profile fields.

No dependency installation is needed for the web interface as it uses Python's
standard library.

Start the local server:

```bash
python web_player_lookup.py
```

Then open this URL in your browser:

```text
http://127.0.0.1:8000
```

If your machine only exposes Python 3 as `python3`, use:

```bash
python3 web_player_lookup.py
```

Stop the server any time with `Ctrl+C` in the terminal where it is running.



## Remote Demo With Ngrok

To let a friend test the web page without downloading the repo, run the local
server first:

```bash
python web_player_lookup.py
```

In a second terminal, start an ngrok tunnel:

```bash
ngrok http 8000
```

Send your friend the public `https://...ngrok-free.app` URL that ngrok prints.
The link works while your local server and ngrok tunnel are both running.
