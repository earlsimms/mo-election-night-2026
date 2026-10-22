"""National races from a CSV - normally a private-to-edit Google Sheet made readable as CSV.
Accepted URLs: file:<path>; Publish-to-web CSV (https://docs.google.com/spreadsheets/d/e/<PUBID>/pub?gid=0&single=true&output=csv);
Sheets export (https://docs.google.com/spreadsheets/d/<FILE_ID>/export?format=csv&gid=0) - export only works if the sheet is
link-viewable; a plain /edit URL is auto-converted to the export URL.

Columns (header row, exact names): race_id,category,state,district,candidate,party,votes,reporting_pct,called_by,winner,
incumbent_party,status,updated_at,key_race,notes   (status/updated_at/key_race/notes optional for backward compatibility)
One row per candidate. A race row with blank candidate is a placeholder (race shows TOO EARLY).
Honesty rule: 'called' ONLY if winner=1 AND called_by non-empty; a status of 'called' without both is downgraded."""
import csv, io, re
from ..common import fetch, finalize

def sheet_url(u):
    m = re.match(r"https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,})/(edit|view)?[^#]*?(?:#gid=(\d+))?$", u)
    if m and "/d/e/" not in u and "export" not in u:
        return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={m.group(3) or 0}"
    return u

def pnum(s):
    s = (s or "").strip().rstrip("%").replace(",", "")
    return float(s) if s else 0.0

def parse(src):
    url = src["url"]
    if "PASTE" in url.upper():
        raise RuntimeError("National sheet URL not set yet - publish the sheet to web as CSV and paste the URL into config.json")
    text = fetch(sheet_url(url))
    if text.lstrip().startswith("<"):
        raise RuntimeError("Got an HTML page instead of CSV - the sheet is private/not published (Google sign-in page)")
    races = {}
    for r in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        k = (r.get("race_id") or "").strip()
        if not k: continue
        cat, st, d = r["category"].strip().lower(), r["state"].strip().upper(), (r.get("district") or "").strip()
        race = races.setdefault(k, {"raw_title": k, "category": cat, "state": st, "district": d or None, "candidates": [],
                                    "called_by": "", "reporting_pct": None, "incumbent_party": (r.get("incumbent_party") or "").strip(),
                                    "is_measure": False, "level": "national", "updated_at": None, "notes": "", "race_id": k, "key": False})
        race["title"] = {"senate": f"{st} Senate", "governor": f"{st} Governor"}.get(cat, f"{st}-{d} House")
        if k.upper().startswith("SAMPLE"): race["title"] = "SAMPLE (fake) - " + race["title"]; race["sample"] = True
        # sheet key_race flags ignored per Earl (2026-10-21)
        if False and (r.get("key_race") or "").strip().upper() in ("TRUE", "1", "YES", "Y"): race["key"] = True
        if r.get("notes"): race["notes"] = r["notes"].strip()
        if (r.get("notes") or "").lower().startswith("special"): race["title"] += " (special)"
        if (r.get("reporting_pct") or "").strip(): race["reporting_pct"] = max(race["reporting_pct"] or 0, pnum(r["reporting_pct"]))
        if (r.get("updated_at") or "").strip(): race["updated_at"] = r["updated_at"].strip()
        if not (r.get("candidate") or "").strip(): continue
        win = (r.get("winner") or "").strip() == "1" and bool((r.get("called_by") or "").strip())
        if win: race["called_by"] = r["called_by"].strip()
        race["candidates"].append({"name": r["candidate"].strip(), "party": (r.get("party") or "").strip().upper(),
                                   "votes": int(pnum(r.get("votes"))), "winner": win})
    out = []
    for x in races.values():
        rp = x["reporting_pct"]
        x["reporting_text"] = f"{rp:g}% expected vote" if rp is not None else "no votes reported"
        out.append(finalize(x))
    return out
