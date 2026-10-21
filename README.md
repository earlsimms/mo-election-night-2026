# Election Night Live Results (Nov 3, 2026)

Static site (`site/`) + a fetch job (`fetcher/`) that writes `site/data/results.json`.

## Run locally (test with real 2024 Missouri data)
    pip install beautifulsoup4      # plus poppler-utils for pdftotext
    python3 -m fetcher.fetch --config config.test2024.json
    cd site && python3 -m http.server 8000    # open http://localhost:8000
    python3 tests/test_all.py

## Election night (local)
    python3 -m fetcher.fetch --config config.json --loop 120    # polls every 2 min (floor: 60s)
Edit `config.json` URLs when counties publish November links (St. Charles LVT index number, St. Louis County `el261103`).
National: publish a Google Sheet (File > Share > Publish to web > CSV) with the columns in `sample/national_sample.csv` and paste its URL.

## Swap a source
Add `fetcher/adapters/<name>.py` with `parse(src_cfg) -> [race dicts]`, register in `fetcher/adapters/__init__.py`, set `"adapter"` in config.

## Deploy (GitHub Pages)
`.github/workflows/update-results.yml` runs on push, manually, and on a schedule, and force-pushes `site/` to the `gh-pages` branch.
Pages source: Settings > Pages > Deploy from a branch > `gh-pages` / root.
Before 6 PM CT Nov 3 it deploys the committed PREVIEW data (2024 MO + SAMPLE national). From then through Nov 6 it polls every ~2 min.
GitHub cron minimum is 5 min and runs are often late; for fresher data run `--loop 120` on an always-on PC (also avoids Cloudflare
blocking datacenter IPs at enr.sos.mo.gov).

## National calls sheet
Google Sheet "Election Night 2026 - National Calls" (private). Template: `sample/national_calls_template.csv`.
To feed the site: File > Share > Publish to web > (sheet) > CSV, then paste the URL into `config.json` (national source `url`).
