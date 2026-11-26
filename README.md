# MLB Player Lookup

A small MLB player lookup tool for finding player profiles by name or MLBAM
ID. The repo includes a quick terminal script `lookup.py` and a lightweight local web
interface `web.py`.  
  
No dependency installation is needed for the web interface as it uses Python's
standard library.


## Method 1. Quick Terminal Lookup

Look up by player name:

```bash
python lookup.py --name "Shohei Ohtani"
```

Look up by MLBAM ID:

```bash
python lookup.py --id 660271
```

To open a player headshot in browser (either `--name` or `--id` works):

```bash
python lookup.py --name "Shohei Ohtani" --show-photo
```

*Note: headshot will only show up if there is only one exact match.*  
*For example, `--name "Max Muncy" --show-photo` would not open the player photo because there are multiple Max Muncy.*  
*However you can still find the unique id for each Max Muncy, then use that id to look up the headshot.*



## Method 2. Web Interface

The web app lets you search with one box, using either a player name or an
MLBAM ID. Each result shows a player headshot, a short lookup summary, and a
per-player "Show details" section for the full profile fields.



Start the local server:

```bash
python web.py
```

Then open this URL in your browser:

```text
http://127.0.0.1:8000
```




### Instruction for Ngrok

To share it with a friend using Ngrok, make sure you have your Ngrok account and authtoken ready. 
```bash
ngrok config add-authtoken AUTHTOKEN
```

You have to run the script on your local server first (follow the instruction above). Then in a second terminal: 

```bash
ngrok http 8000
```

The web will be running on `https://...ngrok-free.app` that ngrok prints.
The link works while your local server and ngrok tunnel are both running.


## Running with Docker

The image runs the web interface by default and binds to the `PORT` env
variable (defaults to `8000`).

Build the image:

```bash
docker build -t mlb-player-lookup .
```

Run the web interface:

```bash
docker run --rm -p 8000:8000 mlb-player-lookup
```

Then open `http://localhost:8000` in your browser.

To use a different port, set `PORT` and map the matching host port:

```bash
docker run --rm -e PORT=5050 -p 5050:5050 mlb-player-lookup
```

Run a one-off CLI lookup in the same image instead of the web server:

```bash
docker run --rm mlb-player-lookup python lookup.py --name "Shohei Ohtani"
```

Or run a CLI lookup against an already-running web container:

```bash
docker exec <container_name_or_id> python lookup.py --id 660271
```


## Deploying to Render

This repo has no `render.yaml`, so the service is configured directly in the
Render dashboard. To deploy with Docker instead of Render's native Python
runtime:

1. In the Render dashboard, open the service (or **New +** → **Web Service**
   when creating one) and set **Runtime** to **Docker**.
2. Leave **Dockerfile Path** as the default (`./Dockerfile`) — no build or
   start command is needed; Render uses `CMD ["python", "web.py"]` from the
   Dockerfile.
3. Don't set a `PORT` environment variable yourself — Render injects its own
   `PORT` value at runtime, and `web.py` already reads it and binds
   `0.0.0.0` to that port.
4. Deploy. Render builds the image from the Dockerfile on every push instead
   of running `pip install` against the repo directly.
