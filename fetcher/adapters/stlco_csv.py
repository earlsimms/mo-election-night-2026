"""St. Louis County BOE precinct CSV (VERIFIED format: extcontent.stlouisco.com/BOE/eResults/el<yymmdd>/CSV.csv).
Columns: Precinct, Precinct ID, Precinct Reporting ('Polls Reporting: a/b'), ..., Contest Title, Contest ID, Contest Party, Choice Name, Choice ID, Choice Party, Total Votes"""
import csv, io, re
from ..common import fetch, classify, finalize, party, split_party

def parse(src):
    text = fetch(src["url"], timeout=60).lstrip("\ufeff#")
    rows = csv.DictReader(io.StringIO(text))
    races, rep = {}, (None, None)
    for r in rows:
        title = re.sub(r"\s+", " ", r["Contest Title"]).strip()
        cp = (r.get("Contest Party") or "").strip()
        m = re.search(r"(\d+)\s*/\s*(\d+)", r.get("Precinct Reporting", ""))
        if m: rep = (int(m.group(1)), int(m.group(2)))
        race = races.setdefault(title, {"raw_title": title, "primary_party": party(cp), "cand": {}})
        nm, p = split_party(r["Choice Name"])
        c = race["cand"].setdefault(nm, {"name": nm.title(), "party": party(r.get("Choice Party")) or p, "votes": 0})
        c["votes"] += int(r["Total Votes"] or 0)
    out = []
    for t, race in races.items():
        base = re.sub(r"\s*-\s*(REPUBLICAN|DEMOCRATIC|LIBERTARIAN|GREEN|CONSTITUTION)\s*$", "", t)
        cat, label, dist = classify(base, county=None if re.search(r"U\.?S\.?|STATE (SENAT|REPRESENT)|AUDITOR|AMENDMENT", base.upper()) else src.get("county"))
        if cat != "county": label = f"{src['county']}: {label}"  # county slice of a state race
        cat = src.get("category") or "county"  # per-county tab category from config (e.g. county_stl)
        if race["primary_party"]: label += f" ({race['primary_party']} primary)"
        cands = [c for c in race["cand"].values() if c["name"].upper() != "NO CANDIDATE FILED"]
        rr = {"raw_title": t, "title": label, "category": cat, "district": dist, "state": "MO", "county": src.get("county"),
              "reporting_pct": round(100 * rep[0] / rep[1], 1) if rep[1] else None,
              "reporting_text": f"{rep[0]} of {rep[1]} polling places" if rep[1] else "", "candidates": cands,
              "is_measure": any(c["name"].upper() in ("YES", "NO") for c in cands)}
        out.append(finalize(rr))
    return out
