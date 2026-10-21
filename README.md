# Election Night Live Results (Nov 3, 2026)

Static site (`site/`) + a fetch job (`fetcher/`) that writes `site/data/results.json`.

## Run locally (test with real 2024 Missouri data)
    pip install beautifulsoup4      # plus poppler-utils for pdftotext
    python3 -m fetcher.fetch --config elections/preview-2024/config.json
    cd site && python3 -m http.server 8000    # open http://localhost:8000
    python3 tests/test_all.py

## Election night (local)
    python3 -m fetcher.fetch --loop 120    # uses the config named in elections/ACTIVE    # polls every 2 min (floor: 60s)
Edit `elections/2026-11-03/config.json` URLs when counties publish November links (St. Charles LVT index number, St. Louis County `el261103`).
National: publish a Google Sheet (File > Share > Publish to web > CSV) with the columns in `elections/2026-11-03/national_calls_template.csv` and paste its URL.

## Swap a source
Add `fetcher/adapters/<name>.py` with `parse(src_cfg) -> [race dicts]`, register in `fetcher/adapters/__init__.py`, set `"adapter"` in config.

## Deploy (GitHub Pages)
`.github/workflows/update-results.yml` runs on push, manually, and on a schedule, and force-pushes `site/` to the `gh-pages` branch.
Pages source: Settings > Pages > Deploy from a branch > `gh-pages` / root.
Before 6 PM CT Nov 3 it deploys the committed PREVIEW data (2024 MO + SAMPLE national). From then through Nov 6 it polls every ~2 min.
GitHub cron minimum is 5 min and runs are often late; for fresher data run `--loop 120` on an always-on PC (also avoids Cloudflare
blocking datacenter IPs at enr.sos.mo.gov).

## National calls sheet
Google Sheet "Election Night 2026 - National Calls" (private). Template: `elections/2026-11-03/national_calls_template.csv`.
To feed the site: File > Share > Publish to web > (sheet) > CSV, then paste the URL into `elections/2026-11-03/config.json` (national source `url`).

## Setting up a new election
Everything election-specific lives in `elections/<YYYY-MM-DD>/`; code in `fetcher/` and `site/` is generic.
1. Copy `elections/2026-11-03/` to `elections/<new date>/`.
2. In its `config.json` set `election`, `election_date`, `live_start_utc` / `live_end_utc` (UTC; poll window), `highlight`
   (race titles such as "MO House 96"), `baselines` (seats NOT up, per chamber), and each source `url` (new SOS page,
   St. Louis County `el<yymmdd>`, St. Charles LVT index number, published national sheet CSV). Set `enabled:false` to drop a source.
3. Replace `measures.json` with the new official ballot titles (or delete `measures_file` from config).
4. Regenerate the national race list CSV (one row per race; format in the template header) and load it into a new Google Sheet.
5. Write the config path into `elections/ACTIVE`, and update the date in the election-window `cron` line of the workflow.
6. Optional: add a preview config (see `elections/preview-2024/`) with `preview_banner` and commit its output as `site/data/results.json`.

## Key races
Mark races as "key" (gold badge, sorted first, "Key races only" filter, "★ Key races" tab):
- Missouri/any race: add its title (e.g. `MO House 96`, `Amendment 6`, `MO US House 2`) or a national race_id to `key_races` in the election config.
- National races: set `key_race` = `TRUE` (or FALSE) in the calls sheet.

## State results feeds (vote counts only)
Adapters in `fetcher/adapters/state_feeds.py`: `nc_enr`, `ga_ev`, `mn_txt`, `pa_api`, `fl_dos`, `wa_sos` (formats checked against 2024 archives)
and `clarity` (best effort, untested). Each source lists `contests` with `race_id`, `category`, `state`, optional `district`, and a `match`
regex for the feed's contest name. Feed votes replace sheet votes for the same race_id; calls ALWAYS come from the sheet
(`winner=1` + `called_by`). `registry/state_feeds_all50.json` lists the known feed for every state, so use it to add states in future elections.
