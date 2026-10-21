# 2026 General (Nov 3) – State live results feed research
Researched 2026-10-21 (CT). Fetch tests run from this box (cloud datacenter IP, curl w/ browser UA).
**Caveat:** race list is based on Cook/Sabato competitive ratings as of mid-2026 knowledge; ratings were NOT re-verified live for Oct 2026 — re-check cookpolitical.com / centerforpolitics.org before finalizing.

## Key races (Toss-up/Lean)
Senate: GA (Ossoff), MI (open), NC (open), ME (Collins), NH (open), OH special (Husted), TX, IA (open), AK, NE (Osborn-I), MN (open).
Governor: AZ, GA, MI, WI, NV, PA, KS, IA, ME, MN, OH, NH.

## State feeds
| State | Race(s) | Feed URL / pattern | Format | Tested | Blockers | Recommendation |
|---|---|---|---|---|---|---|
| NC | Sen | `https://er.ncsbe.gov/enr/YYYYMMDD/data/results_0.txt` (live); `https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/YYYY_MM_DD/results_pct_YYYYMMDD.zip` | JSON-ish txt; precinct TSV zip | YES – 2024 both 200 (216 KB txt, 3.7 MB zip) | None seen; S3 public | **Best-in-class. Use.** ~5-min refresh on election night |
| GA | Sen, Gov | `https://results.sos.ga.gov/cdn/results/Georgia/export-<ElectionSlug>.json` (Enhanced Voting; replaced Clarity in 2024) | JSON | YES – 2024NovGen 200 (33.7 MB) | Old Clarity GA endpoints 403; file is large | **Use**; poll ETag/size, 2–5 min |
| PA | Gov | `https://www.electionreturns.pa.gov/api/ElectionReturn/<Method>?methodName=...` (GetAllElections, GetCountyBreak…) | JSON (undocumented) | YES – GetAllElections 200 (39 KB) | Undocumented API, params change; no ToS for reuse stated | Use cautiously, test on Nov 3 morning |
| MN | Sen, Gov | `https://electionresultsfiles.sos.mn.gov/YYYYMMDD/<file>.txt` (e.g. ussenate.txt); index at electionresults.sos.mn.gov MediaResult | semicolon-delimited TXT | YES – 20241105/ussenate.txt 200 | None | **Use**; documented media files, frequent updates |
| OH | Sen, Gov | `https://liveresults.ohiosos.gov/` (has downloadable results files on night) | HTML + XML/CSV downloads | Partial – site 200, no archive file tested | Archive removed post-certification | Viable; confirm download links when live |
| AZ | Gov | `https://results.arizona.vote/` (Enhanced Voting JSON behind) | JSON | YES – **403 Cloudflare challenge** | Cloudflare blocks datacenter IPs | Likely fails from GitHub Actions; use AP/news fallback or residential proxy (check ToS) |
| TX | Sen | `https://results.texas-election.com/` (Civix) | JSON behind SPA | YES – **403 Cloudflare** | Cloudflare | Likely blocked from cloud |
| MI | Sen, Gov | `https://mielections.us/election/results/` | HTML; county-level downloads | YES – connection timeout (000) | Geo/IP filtering suspected | Unreliable from cloud; counties (Clarity) as fallback |
| IA | Sen, Gov | `https://electionresults.iowa.gov/IA/<electionId>/` (Clarity ENR: `.../json/en/summary.json`, `current_ver.txt`) | JSON/XML zip | Partial – 301/404 on guessed 2024 ID | Need current election ID; Clarity CDN sometimes 403s bots | Viable once ID known |
| KS | Gov | Clarity `https://results.enr.clarityelections.com/KS/<id>/` | JSON/XML | Partial – root 200 | Need ID | Viable |
| NV | Gov | `https://silverstateelection.nv.gov/` (JSON/XML/CSV downloads on night) | JSON/XML/CSV | Partial – 200 stub (212 B, JS redirect) | Archive offline | Viable; verify Nov 3 |
| WI | Gov | No statewide live feed (WEC posts after canvass); counties only (Milwaukee, Dane Clarity) | Mixed | No | Fragmented | Use AP/news; counties optional |
| ME | Sen, Gov | No live feed; SOS posts XLSX days later (RCV) | XLSX | No | No live data | Don't rely on state |
| NH | Sen, Gov | No live state feed; SOS posts town XLSX after | XLSX | No | No live data | Don't rely on state |
| AK | Sen | `https://www.elections.alaska.gov/results/<YYGENR>/` (txt/PDF summaries; RCV tabs later) | TXT/PDF | YES – timeout (000) | Blocks/slow from cloud | Unreliable |
| NE | Sen | `https://electionresults.nebraska.gov/` | HTML/CSV | No | – | Low priority, verify |

## National sources
- **OpenElections** (github.com/openelections, raw GitHub tested 200): free CSV, **post-election** only, weeks–months lag.
- **MIT Election Data + Science Lab** (Harvard Dataverse): free, **post-election**, certified county/precinct.
- **Google Civic Information API**: representatives endpoint retired Apr 2025; election/voter-info only — **no results**.
- **AP Elections API / Decision Desk HQ**: live, authoritative but **paid** (not free).
- **Clarity/Scytl ENR** (many counties): JSON/XML, live, free to read; per-county election IDs needed.

## Bottom line
Reliable free live feeds from cloud: **NC, GA, MN, PA** (tested), likely **OH, IA, KS, NV** (verify on night). **AZ, TX** Cloudflare-blocked from datacenter IPs; **MI, AK** timed out; **WI, ME, NH** have no live statewide feed. GitHub Actions shares the same datacenter-IP issue and has ≥5-min cron granularity (often delayed) — expect same blocks. No ToS forbidding reading public results found, but none grant reuse rights explicitly; poll politely (≥60 s, cache, honor ETag).
