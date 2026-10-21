"""Missouri Secretary of State.
parse_pdf: VERIFIED against the official 2024 general-election returns PDF (sos.mo.gov/CMSImages/ElectionResultsStatistics/...).
parse_enr: best-effort HTML scrape of enr.sos.mo.gov (Cloudflare blocks cloud/datacenter IPs, so structure could not be verified
           from this box). It looks for any table rows of candidate/party/votes under contest headings with 'Precincts Reported'."""
import re, os, subprocess, tempfile
from ..common import fetch, classify, finalize, party, ROOT

HDR = re.compile(r"^\s*(\S.*?)\s{2,}\((\d+) of (\d+) Precincts Reported\)")
ROW = re.compile(r"^\s*(\S.*?)\s{2,}(\S.*?)\s{2,}([\d,]+)\s+([\d.]+)%\s*$")
YN = re.compile(r"(Yes|No) Votes\s+([\d,]+)\s+([\d.]+)%")

def parse_text(txt, official):
    races, cur = [], None
    for line in txt.splitlines():
        h = HDR.match(line)
        if h:
            cur = {"raw_title": h.group(1).strip(), "reporting_pct": round(100 * int(h.group(2)) / max(1, int(h.group(3))), 1),
                   "reporting_text": f"{h.group(2)} of {h.group(3)} precincts", "candidates": []}
            races.append(cur); continue
        if not cur or "Total Votes" in line: continue
        y = YN.search(line)
        if y:
            cur["candidates"].append({"name": y.group(1), "party": "", "votes": int(y.group(2).replace(",", ""))}); continue
        r = ROW.match(line)
        if r and not r.group(1).startswith("Office/"):
            cur["candidates"].append({"name": r.group(1).strip(), "party": party(r.group(2)), "votes": int(r.group(3).replace(",", ""))})
    out = []
    for r in races:
        cat, label, dist = classify(r["raw_title"])
        if cat == "mo_other" and ("Judge" in label or "Court" in label): cat = "mo_judicial"
        r.update(category=cat, title=label, district=dist, state="MO",
                 is_measure=any(c["name"] in ("Yes", "No") for c in r["candidates"]))
        out.append(finalize(r, official=official))
    return out

def parse_pdf(src):
    cache = src.get("cache_file")
    path = os.path.join(ROOT, cache) if cache else None
    if not path or not os.path.exists(path):
        data = fetch(src["url"], binary=True, timeout=60)
        path = path or tempfile.mktemp(suffix=".pdf")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(data)
    txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout
    return parse_text(txt, official="Official" in txt[:500])

def parse_enr(src):
    from bs4 import BeautifulSoup
    html = fetch(src["url"])
    if "Attention Required! | Cloudflare" in html or "Sorry, you have been blocked" in html:
        raise RuntimeError("Blocked by Cloudflare at enr.sos.mo.gov (try running the job from a residential IP / self-hosted runner)")
    txt = BeautifulSoup(html, "html.parser").get_text("\n")
    # Normalise ENR text into the same 'Title  (x of y Precincts Reported)' layout and reuse the verified parser.
    txt = re.sub(r"\n\s*\((\d+) of (\d+) Precincts Reported\)", r"   (\1 of \2 Precincts Reported)", txt)
    races = parse_text(txt, official=bool(re.search(r"Official Results", html)))
    if not races:
        raise RuntimeError("enr.sos.mo.gov page fetched but no contests recognised - page layout changed; update mo_sos.parse_enr")
    return races
