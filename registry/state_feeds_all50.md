# All-states official results feed registry (2026-10-21)

One polite GET per state from this cloud box (2 s apart). 'working' = archive data file fetched OK; 'probably' = site reachable, data endpoint unverified; 'blocked' = 403/Cloudflare/timeout; 'none' = no live statewide feed. Feed patterns are from prior cycles (2022/2024) — verify on election morning.

|State|Official site|Feed pattern|Format|Vendor|Tested (result)|Blockers|Live night|Class|Election-ID notes|
|-|-|-|-|-|-|-|-|-|-|
|AL|https://www2.alabamavotes.gov/electionnight/|`ENR HTML + CSV export`|CSV/HTML|custom (SOS)|yes: 200 (501 bytes)||yes|probably|Election picked by dropdown; CSV export link per race|
|AK|https://www.elections.alaska.gov/results/|`/results/{YY}GENR/ summary txt/PDF`|TXT/PDF|custom|yes: timeout/no connection|timeout|yes|blocked|Folder code e.g. 24GENR; RCV tabulation posted later|
|AZ|https://results.arizona.vote/|`Enhanced Voting JSON behind SPA`|JSON|Enhanced Voting|yes: 403 blocked (Cloudflare)|Cloudflare|yes|blocked|Election slug in SPA URL|
|AR|https://results.enr.clarityelections.com/AR/|`Clarity /AR/{id}/json/en/summary.json; current_ver.txt`|JSON/XML zip|Clarity (Scytl)|yes: 403 blocked|403|yes|blocked|ID from SOS election-results page link|
|CA|https://electionresults.sos.ca.gov/|`/returns/... JSON via site API; api endpoints e.g. https://api.sos.ca.gov/returns/`|JSON|custom (SOS)|yes: 200 (62369 bytes)||yes|probably|Statewide only; counties count for weeks|
|CO|https://results.enr.clarityelections.com/CO/|`Clarity /CO/{id}/`|JSON/XML zip|Clarity (Scytl)|yes: 200 (4440 bytes)||yes|probably|ID linked from sos.state.co.us|
|CT|https://electionhistory.ct.gov/|`ElectionStats; live via ctemspublic.pcctg.net`|HTML/CSV|custom/ElectionStats|yes: 200 (77167 bytes)||yes|probably|Live ENR at ctemspublic; history post-cert|
|DE|https://elections.delaware.gov/results/|`/results/html/index.shtml?electionId=GE{YYYY}`|HTML|custom|yes: 200 (39731 bytes)||yes|probably|electionId=GE2024 style|
|DC|https://electionresults.dcboe.org/|`election_results/{date}-General-Election; XML/CSV downloads`|XML/CSV|custom (DCBOE)|yes: 200 (4450 bytes)||yes|probably|Date-based path|
|FL|https://results.elections.myflorida.com/|`Downloadable results: /downloadresults.asp?ElectionDate=MM/DD/YYYY`|TXT tab-delimited|custom (DOS)|yes: 200 (2043 bytes)||yes|working|ElectionDate param|
|GA|https://results.sos.ga.gov/|`/cdn/results/Georgia/export-{Slug}.json`|JSON|Enhanced Voting|yes: 200 (10622 bytes)||yes|working|Slug e.g. 2024NovGen from site URL|
|HI|https://elections.hawaii.gov/election-results/|`Summary PDF/TXT per printout`|PDF/TXT|custom|yes: 200 (185611 bytes)||yes|probably|Printout number per release|
|ID|https://results.sos.idaho.gov/|`Enhanced Voting-style JSON`|JSON|Enhanced Voting|yes: timeout/no connection|timeout|yes|blocked|Slug in URL|
|IL|https://www.elections.il.gov/electionoperations/ElectionVoteTotals.aspx|`No statewide live; counties (Clarity Cook/Chicago)`|HTML|custom|yes: 200 (272585 bytes)||no|none|Live via Cook County/Chicago BOE|
|IN|https://enr.indianavoters.in.gov/|`JSON via site`|JSON|custom (Civix?)|yes: 200 (16333 bytes)||yes|probably|Election in URL hash|
|IA|https://electionresults.iowa.gov/|`Clarity /IA/{id}/`|JSON/XML zip|Clarity (Scytl)|yes: 200 (4440 bytes)||yes|probably|ID from sos.iowa.gov|
|KS|https://results.enr.clarityelections.com/KS/|`Clarity /KS/{id}/`|JSON/XML zip|Clarity (Scytl)|yes: 200 (3100 bytes)||yes|probably|ID from sos.ks.gov|
|KY|https://results.enr.clarityelections.com/KY/|`Clarity /KY/{id}/`|JSON/XML zip|Clarity (Scytl)|yes: 403 blocked|403|yes|blocked|ID from elect.ky.gov|
|LA|https://voterportal.sos.la.gov/graphical|`JSON API behind voterportal`|JSON|custom (SOS)|yes: 200 (35210 bytes)||yes|probably|Election date selector; La. general is Nov jungle|
|ME|https://www.maine.gov/sos/cec/elec/results/|`XLSX post-election`|XLSX|custom|yes: 403 blocked|403|no|none|Year folder; no live|
|MD|https://elections.maryland.gov/elections/|`/elections/{YYYY}/results/general/ CSV`|HTML/CSV|custom|yes: 200 (15782 bytes)||yes|probably|Year path|
|MA|https://electionstats.state.ma.us/|`ElectionStats; no live statewide`|HTML/CSV|ElectionStats|yes: 200 (343705 bytes)||no|none|Post-cert only|
|MI|https://mielections.us/election/results/|`HTML + county downloads`|HTML|custom|yes: timeout/no connection|timeout|yes|blocked|Election path by date|
|MN|https://electionresultsfiles.sos.mn.gov/|`/{YYYYMMDD}/{file}.txt (ussenate.txt etc)`|semicolon TXT|custom (SOS)|yes: 200 (395 bytes)||yes|working|Date folder; file list on MediaResult page|
|MS|https://www.sos.ms.gov/elections-voting/election-results|`No reliable live feed; county PDFs`|PDF|custom|yes: 200 blocked (Cloudflare)|Cloudflare|no|none|Post-election|
|MO|https://enr.sos.mo.gov/|`ENR XML/CSV downloads`|XML/HTML|custom (SOS)|yes: 200 (24106 bytes)||yes|probably|Election ID in query|
|MT|https://electionresults.mt.gov/|`JSON via site`|JSON|custom|yes: 403 blocked (Cloudflare)|Cloudflare|yes|blocked|Election in URL|
|NE|https://electionresults.nebraska.gov/|`/resultsSW.aspx?type=...`|HTML/CSV|custom|yes: 200 (54947 bytes)||yes|probably|Static path per election|
|NV|https://silverstateelection.nv.gov/|`JSON/XML/CSV downloads on night`|JSON/XML/CSV|custom|yes: 200 (212 bytes)|post-cert takedown|yes|probably|Archive removed post-cert|
|NH|https://www.sos.nh.gov/elections/elections/election-results|`Town XLSX post-election`|XLSX|custom|yes: 403 blocked|403|no|none|Year folder|
|NJ|https://www.nj.gov/state/elections/election-information-results.shtml|`No statewide live; county Clarity`|HTML/PDF|custom|yes: 200 (63253 bytes)||no|none|Counties via Clarity/NJ county sites|
|NM|https://electionresults.sos.nm.gov/|`Enhanced Voting-style JSON`|JSON|custom/Enhanced Voting|yes: 403 blocked|403|yes|blocked|Slug in URL|
|NY|https://nyenr.elections.ny.gov/|`HTML ENR; CSV export`|HTML/CSV|custom (BOE)|yes: 403 blocked (Cloudflare)|Cloudflare|yes|blocked|Single page per election|
|NC|https://er.ncsbe.gov/|`/enr/{YYYYMMDD}/data/results_0.txt; s3 dl.ncsbe.gov/ENRS/{YYYY_MM_DD}/results_pct_{YYYYMMDD}.zip`|JSON txt / TSV zip|custom (NCSBE)|yes: 200 (216378 bytes)||yes|working|Date-based, predictable|
|ND|https://results.sos.nd.gov/|`ASP.NET results; CSV export`|HTML/CSV|custom|yes: 200 (82821 bytes)||yes|probably|Election dropdown|
|OH|https://liveresults.ohiosos.gov/|`Live HTML + XML/CSV downloads`|XML/CSV|custom|yes: 200 (67573 bytes)|post-cert takedown|yes|probably|Archive removed post-cert|
|OK|https://results.okelections.gov/|`OK ENR; XML/CSV export`|XML/CSV|custom (OSEB)|yes: 403 blocked|403|yes|blocked|Election date in URL|
|OR|https://results.oregonvotes.gov/|`ENR HTML; CSV`|HTML/CSV|custom|yes: 200 (92256 bytes)||yes|probably|Mail vote; slow count|
|PA|https://www.electionreturns.pa.gov/|`/api/ElectionReturn/{Method}?methodName=...&electionid={id}`|JSON (undocumented)|custom|yes: 200 (39134 bytes)||yes|working|GetAllElections lists IDs|
|RI|https://enr.ri.gov/|`ENR with downloads`|HTML/CSV|Clarity-like/custom|yes: timeout/no connection|timeout|yes|blocked|Election in path|
|SC|https://results.enr.clarityelections.com/SC/|`Clarity /SC/{id}/`|JSON/XML zip|Clarity (Scytl)|yes: 200 (4440 bytes)||yes|probably|ID from scvotes.gov|
|SD|https://electionresults.sd.gov/|`ENR HTML`|HTML|custom|yes: 200 (44183 bytes)||yes|probably|Election dropdown|
|TN|https://sos.tn.gov/elections/results|`Live JSON at elections.tn.gov results app`|JSON/HTML|custom|yes: 403 blocked|403|yes|blocked|Check SOS page on night|
|TX|https://results.texas-election.com/|`Civix JSON behind SPA`|JSON|Civix|yes: 200 (2095 bytes)||yes|probably|Election ID in SPA|
|UT|https://electionresults.utah.gov/|`Enhanced Voting-style JSON`|JSON|Enhanced Voting|yes: 200 (9684 bytes)||yes|probably|Slug in URL|
|VT|https://electionarchive.vermont.gov/|`ElectionStats; live via SOS page`|HTML/CSV|ElectionStats|yes: 200 (77831 bytes)||yes|probably|Live results page on sos.vermont.gov|
|VA|https://enr.elections.virginia.gov/|`/results/public/api/... (Enhanced Voting); historical XML/CSV on historical site`|JSON|Enhanced Voting|yes: 200 (37839 bytes)||yes|probably|Slug in URL|
|WA|https://results.vote.wa.gov/|`/results/{YYYYMMDD}/export/{YYYYMMDD}_AllState.csv`|CSV|custom (SOS)|yes: 200 (58588 bytes)||yes|working|Date-based, predictable|
|WV|https://results.enr.clarityelections.com/WV/|`Clarity /WV/{id}/`|JSON/XML zip|Clarity (Scytl)|yes: 200 (4440 bytes)||yes|probably|ID from sos.wv.gov|
|WI|https://elections.wi.gov/elections/election-results|`No statewide live; counties`|XLSX post-cert|custom|yes: 403 blocked (Cloudflare)|Cloudflare|no|none|Post-canvass|
|WY|https://sos.wyo.gov/Elections/State/Results.aspx|`PDF/HTML summaries`|PDF/HTML|custom|yes: 404 (3907 bytes)||no|none|Unofficial PDFs on night|

## Summary
- **probably** (25): AL, CA, CO, CT, DE, DC, HI, IN, IA, KS, LA, MD, MO, NE, NV, ND, OH, OR, SC, SD, TX, UT, VT, VA, WV
- **blocked** (12): AK, AZ, AR, ID, KY, MI, MT, NM, NY, OK, RI, TN
- **working** (6): FL, GA, MN, NC, PA, WA
- **none** (8): IL, ME, MA, MS, NH, NJ, WI, WY

National: OpenElections & MIT Election Lab = free, post-election only; Google Civic = no results; AP/DDHQ = live but paid; county Clarity = free live, per-county IDs.