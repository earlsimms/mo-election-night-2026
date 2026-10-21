"""Shared helpers: polite HTTP, normalization, race classification, status logic."""
import re, time, urllib.request, os, io

UA = "MO-Election-Dashboard/1.0 (non-commercial results viewer; polls every few minutes)"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fetch(url, timeout=30, binary=False):
    if url.startswith("file:"):
        p = os.path.join(ROOT, url[5:])
        return open(p, "rb").read() if binary else open(p, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", errors="replace")

def num(s):
    s = re.sub(r"[^\d.]", "", str(s or ""))
    return float(s) if "." in s else int(s) if s else 0

PARTY = {"republican": "R", "rep": "R", "democratic": "D", "democrat": "D", "dem": "D", "libertarian": "L", "lib": "L",
         "green": "G", "grn": "G", "constitution": "C", "better": "B", "independent": "I", "ind": "I", "write-in": "W"}
def party(p):
    p = (p or "").lower().replace(" party", "").strip()
    return PARTY.get(p, p[:3].upper() if p else "")

def split_party(name):
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", name or "")
    return (m.group(1).strip(), party(m.group(2))) if m else ((name or "").strip(), "")

def classify(title, county=None):
    """Return (category, label, district) for a raw contest title."""
    t = re.sub(r"\s+", " ", title).strip()
    u = t.upper()
    d = re.search(r"DISTRICT\s*(\d+)", u)
    dist = int(d.group(1)) if d else None
    if re.search(r"\b(PRESIDENT)\b", u): return "mo_statewide", "U.S. President", None
    if re.search(r"U\.?S\.? SENAT", u): return "mo_statewide", "U.S. Senator (MO)", None
    if re.search(r"U\.?S\.? REPRESENTATIVE|CONGRESS", u): return "mo_ushouse", f"MO US House {dist}", dist
    if re.search(r"STATE SENAT", u): return "mo_senate", f"MO Senate {dist}", dist
    if re.search(r"STATE REPRESENTATIVE", u): return "mo_house", f"MO House {dist}", dist
    if re.search(r"CONSTITUTIONAL AMENDMENT|^AMENDMENT|STATEWIDE.*(AMENDMENT|PROPOSITION)", u):
        n = re.search(r"AMENDMENT\s*(?:NO\.?\s*)?(\w+)", u); return "mo_measure", f"Amendment {n.group(1) if n else '?'}", None
    if re.match(r"^(STATEWIDE )?PROPOSITION [A-Z]$", u) and not county:
        return "mo_measure", t.title().replace("Proposition", "Proposition"), None
    for off in ["GOVERNOR", "LIEUTENANT GOVERNOR", "SECRETARY OF STATE", "STATE TREASURER", "ATTORNEY GENERAL", "STATE AUDITOR"]:
        if u == off or u.startswith(off + " ") and "COUNTY" not in u:
            return "mo_statewide", off.title(), None
    if county: return "county", f"{county}: {t.title()}", dist
    return "mo_other", t, dist

def finalize(race, source_called=False, official=False):
    """Status honesty: 'called' only if the source flags a winner; 'certified' if the source says official/final;
    otherwise 'leading' (with % reporting) or 'too_early' when nothing is reported."""
    c = race["candidates"]
    tot = sum(x["votes"] for x in c) or 0
    for x in c:
        x["pct"] = round(100 * x["votes"] / tot, 1) if tot else 0.0
    c.sort(key=lambda x: -x["votes"])
    race["total_votes"] = tot
    rp = race.get("reporting_pct")
    if official:
        race["status"] = "certified"
    elif source_called or any(x.get("winner") for x in c):
        race["status"] = "called"
    elif tot == 0 or (rp is not None and rp == 0):
        race["status"] = "too_early"
    else:
        race["status"] = "leading"
    if c and race["status"] in ("certified",) and tot:
        c[0]["winner"] = True if len(c) < 2 or c[0]["votes"] > c[1]["votes"] else False
    if len(c) >= 2 and tot:
        race["margin_pct"] = round(c[0]["pct"] - c[1]["pct"], 1)
    return race
