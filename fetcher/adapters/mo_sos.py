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

PREC = re.compile(r"^(\d[\d,]*) of (\d[\d,]*) Precincts Reported$")

def _session():
    """enr.sos.mo.gov sits behind a Cloudflare challenge that rejects plain urllib (403 'cf-mitigated: challenge') but
    serves a browser-TLS client (curl_cffi impersonate=chrome). Installed lazily so an already-running job picks it up."""
    try:
        from curl_cffi import requests as cr
    except ImportError:
        import sys
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--user", "curl_cffi"], capture_output=True, timeout=180)
        import site, importlib; importlib.reload(site)
        try: sys.path.append(site.getusersitepackages())
        except Exception: pass
        from curl_cffi import requests as cr
    return cr.Session(impersonate="chrome")

def parse_enr_text(html):
    from bs4 import BeautifulSoup
    lines = [l.strip() for l in BeautifulSoup(html, "html.parser").get_text("\n").splitlines() if l.strip()]
    races, cur, i = [], None, 0
    while i < len(lines):
        m = PREC.match(lines[i + 1]) if i + 1 < len(lines) else None
        if m:
            a, b = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
            cur = {"raw_title": re.sub(r"\s+", " ", lines[i]).strip(), "reporting_pct": round(100 * a / max(1, b), 1),
                   "reporting_text": f"{a} of {b} precincts", "candidates": []}
            races.append(cur); i += 2; continue
        if cur is not None and lines[i].startswith("Total Votes"):
            cur = None; i += 1; continue
        if cur is not None and i + 2 < len(lines) and re.fullmatch(r"[\d,]+", lines[i + 1]) and lines[i + 2].endswith("%"):
            nm = lines[i]; up = nm.upper()
            if up in ("YES", "NO", "YES VOTES", "NO VOTES"): nm = up.split()[0].title()
            cur["candidates"].append({"name": nm, "party": "", "votes": int(lines[i + 1].replace(",", ""))}); i += 3; continue
        if cur is not None and i + 3 < len(lines) and re.fullmatch(r"[\d,]+", lines[i + 2]) and lines[i + 3].endswith("%"):
            if lines[i].upper() != "WRITE-INS":
                cur["candidates"].append({"name": lines[i], "party": party(lines[i + 1]), "votes": int(lines[i + 2].replace(",", ""))})
            i += 4; continue
        i += 1
    official = bool(re.search(r"Official Results", html))
    out = []
    for r in races:
        cat, label, dist = classify(r["raw_title"])
        if cat == "mo_other" and ("Judge" in label or "Court" in label): cat = "mo_judicial"
        r.update(category=cat, title=label, district=dist, state="MO",
                 is_measure=any(c["name"] in ("Yes", "No") for c in r["candidates"]))
        out.append(finalize(r, official=official))
    return out

def parse_enr(src):
    """GET the ENR page, then replay the ASP.NET 'Submit' postback for the selected election (the page body is
    filled only by that postback), and parse the 'All Results' listing."""
    from bs4 import BeautifulSoup
    base = "https://enr.sos.mo.gov/"
    s = _session()
    r = s.get(base, timeout=40)
    if r.status_code != 200:
        raise RuntimeError(f"enr.sos.mo.gov HTTP {r.status_code} (Cloudflare) on initial GET")
    soup = BeautifulSoup(r.text, "html.parser")
    data = {x["name"]: x.get("value", "") for x in soup.select("input[name]") if x.get("type") != "submit"}
    sel = soup.find("select", id="cboElectionNames")
    if sel is None:
        raise RuntimeError("enr.sos.mo.gov: election selector not found - layout changed")
    opt = sel.find("option", selected=True) or sel.find("option")
    data[sel["name"]] = opt["value"]
    data["ctl00$MainContent$btnElectionType"] = "Submit"
    r2 = s.post(base, data=data, timeout=90)
    if r2.status_code != 200:
        raise RuntimeError(f"enr.sos.mo.gov HTTP {r2.status_code} on results postback")
    races = parse_enr_text(r2.text)
    if not races:
        raise RuntimeError("enr.sos.mo.gov page fetched but no contests recognised - page layout changed; update mo_sos.parse_enr")
    return races
