"""Free official state results feeds (FL, WA added) (vote counts only; calls come from the national calls sheet).
Each source config has "contests": [{"race_id","category","state","district"(opt),"match": regex on the feed's contest name}].
Returned races have level 'state_feed'; fetch.py merges them into national races with the same race_id.
Verified against 2024 archives: NC (er.ncsbe.gov results_0.txt), GA (results.sos.ga.gov export JSON),
MN (electionresultsfiles.sos.mn.gov *.txt), PA (electionreturns.pa.gov API). Clarity (OH/NV/IA/KS etc.) is best-effort, untested."""
import json, re
from ..common import fetch, finalize

PMAP = {"REP": "R", "DEM": "D", "DFL": "D", "LIB": "L", "LBT": "L", "GRE": "G", "GRN": "G", "IND": "I", "NPA": "I", "UNA": "I", "CST": "C"}
def P(p): return PMAP.get((p or "").strip().upper()[:3] if (p or "").upper() not in PMAP else (p or "").upper(), (p or "").strip().upper()[:3])

def _build(src, contests):
    """contests: dict contest_name -> {"cands":[(name,party,votes)], "rep":(a,b) or None}"""
    out = []
    for c in src.get("contests", []):
        rx = re.compile(c["match"], re.I)
        hits = [k for k in contests if rx.search(k)]
        if not hits: continue
        k = hits[0]; v = contests[k]; a, b = v.get("rep") or (None, None)
        st = c["state"]; d = c.get("district")
        title = {"senate": f"{st} Senate", "governor": f"{st} Governor", "house": f"{st}-{d} House"}.get(c["category"], k.title())
        out.append(finalize({"raw_title": c["race_id"], "race_id": c["race_id"], "title": title, "category": c["category"],
            "state": st, "district": d, "level": "state_feed", "feed_contest": k, "is_measure": False,
            "reporting_pct": round(100 * a / b, 1) if b else None,
            "reporting_text": f"{a} of {b} precincts (state feed)" if b else "state feed (no reporting % published)",
            "candidates": [{"name": n, "party": p, "votes": int(x), "winner": False} for n, p, x in v["cands"]]}))
    return out

def nc_enr(src):
    rows = json.loads(fetch(src["url"], timeout=60))
    C = {}
    for r in rows:
        c = C.setdefault(r["cnm"], {"cands": [], "rep": (int(r["prt"]), int(r["ptl"]))})
        c["cands"].append((r["bnm"], P(r["pty"]), int(r["vct"] or 0)))
    return _build(src, C)

def mn_txt(src):
    C = {}
    for url in src["urls"]:
        for line in fetch(url, timeout=60).splitlines():
            f = line.split(";")
            if len(f) < 16: continue
            name = f[4] + (f" {f[5]}" if f[5] else "")
            c = C.setdefault(name, {"cands": [], "rep": (int(f[11] or 0), int(f[12] or 0))})
            c["cands"].append((f[7], P(f[10]), int(f[13] or 0)))
    return _build(src, C)

def ga_ev(src):
    d = json.loads(fetch(src["url"], timeout=120))
    C = {}
    for it in d["results"]["ballotItems"]:
        a, b = it.get("precinctsReporting"), it.get("precinctsParticipating")
        C[it["name"]] = {"rep": (a, b) if b else None,
                         "cands": [(re.sub(r"\s*\((Rep|Dem|Lib|Ind|Grn)\)\s*$", "", o["name"]), P(o.get("politicalParty")), o.get("voteCount") or 0)
                                   for o in it["ballotOptions"]]}
    return _build(src, C)

def pa_api(src):
    raw = fetch(src["url"], timeout=60)
    d = json.loads(raw); d = json.loads(d) if isinstance(d, str) else d
    C = {}
    for office, items in d["Election"].items():
        for it in items:
            key = office + (f" District {it.get('DistrictId')}" if it.get("DistrictId") not in (None, "1") else "")
            C[key] = {"rep": None, "cands": [(x["CandidateName"].title(), P(x["PartyName"]), int(x["Votes"] or 0)) for x in it.get("Statewide", [])]}
    return _build(src, C)

def clarity(src):
    """Clarity/Scytl ENR. src['url'] = base like https://results.enr.clarityelections.com/KS/<electionId>/ (UNTESTED - set ID on Nov 3)."""
    base = src["url"].rstrip("/") + "/"
    ver = fetch(base + "current_ver.txt").strip()
    data = json.loads(fetch(f"{base}{ver}/json/en/summary.json", timeout=60))
    C = {}
    for r in data:
        names, parties, votes = r.get("CH", []), r.get("P", []), r.get("V", [])
        C[r.get("C", "")] = {"rep": (int(r.get("PR", 0) or 0), int(r.get("TP", 0) or 0)),
                            "cands": [(n, P(parties[i] if i < len(parties) else ""), int(votes[i] if i < len(votes) else 0)) for i, n in enumerate(names)]}
    return _build(src, C)

def fl_dos(src):
    """Florida DOS tab-delimited extract (county rows). VERIFIED on 11/5/2024:
    https://results.elections.myflorida.com/ResultsExtract.Asp?ElectionDate=11/5/2024&OfficialResults=N&PartyRaces=N&DataMode=&FormsButton2=Download"""
    import csv, io
    C = {}
    for r in csv.DictReader(io.StringIO(fetch(src["url"], timeout=90)), delimiter="\t"):
        key = r["OfficeDesc"] + (f" District {r['Juris1num']}" if (r.get("Juris1num") or "").strip() else "")
        c = C.setdefault(key, {"cands": {}, "pr": {}, "rep": None})
        nm = f"{r['CanNameFirst']} {r['CanNameLast']}".strip()
        k = (nm, P(r["PartyCode"]))
        c["cands"][k] = c["cands"].get(k, 0) + int(r["CanVotes"] or 0)
        c["pr"][r["CountyCode"]] = (int(r["PrecinctsReporting"] or 0), int(r["Precincts"] or 0))
    for c in C.values():
        a = sum(x[0] for x in c["pr"].values()); b = sum(x[1] for x in c["pr"].values())
        c["rep"] = (a, b) if b else None
        c["cands"] = [(n, p, v) for (n, p), v in c["cands"].items()]
    return _build(src, C)

def wa_sos(src):
    """Washington SOS statewide CSV. VERIFIED: https://results.vote.wa.gov/results/20241105/export/20241105_AllState.csv
    Party text like '(Prefers Democratic Party)'. No % reporting published (WA counts by mail for days)."""
    import csv, io
    C = {}
    for r in csv.DictReader(io.StringIO(fetch(src["url"], timeout=60).lstrip("\ufeff"))):
        pm = re.search(r"Prefers (\w+)", r.get("Party") or "")
        p = {"Democratic": "D", "GOP": "R", "Republican": "R", "Libertarian": "L", "Green": "G", "Independent": "I"}.get(pm.group(1), pm.group(1)[:3].upper()) if pm else ""
        C.setdefault(r["Race"], {"cands": [], "rep": None})["cands"].append((r["Candidate"], p, int(r["Votes"] or 0)))
    return _build(src, C)
