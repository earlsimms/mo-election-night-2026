"""St. Louis Post-Dispatch election results page (graphics.stltoday.com/apps/elections/st-louis-county/).
Fallback for St. Louis County while the BOE CSV (extcontent.stlouisco.com) is unposted and the BOE's own
ENR (stlouis.totalvote.com) refuses datacenter IPs. HTML: div.race > h3 title, p.precincts, tr[data-name] > td.name/td.votes.
Only contests listed in TITLE_MAP are emitted; titles match elections/<date>/mo_placeholders.json so they replace those cards."""
import re
from ..common import fetch, finalize, party

TITLE_MAP = {
    "St. Louis County Executive": "St. Louis County: County Executive",
    "St. Louis County Prosecuting Attorney": "St. Louis County: Prosecuting Attorney",
    "St. Louis County Assessor": "St. Louis County: County Assessor",
    "St. Louis County Council, District 1": "St. Louis County: County Council District 1",
    "St. Louis County Council, District 3": "St. Louis County: County Council District 3",
    "St. Louis County Council, District 5": "St. Louis County: County Council District 5",
    "St. Louis County Council, District 7": "St. Louis County: County Council District 7",
    "St. Louis County Proposition A": "St. Louis County: Proposition A (Charter: County Auditor)",
    "St. Louis County Proposition S": "St. Louis County: Proposition S (Senior Services Tax)",
}

def _get(url, timeout=15):
    try:
        return fetch(url, timeout=timeout)
    except Exception as e1:
        if url.startswith("file:") or "timed out" in str(e1).lower():
            raise  # a timeout means the runner IP is blocked; a browser-TLS retry won't help

        try:
            from curl_cffi import requests as cr
        except ImportError:
            raise e1
        r = cr.get(url, impersonate="chrome", timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} (urllib: {e1})")
        return r.text

def parse(src):
    from bs4 import BeautifulSoup
    html = _get(src["url"], src.get("timeout", 15))
    snap = re.search(r"<!--\s*snapshot\s+(.*?)\s*-->", html[:500])
    via = f"via St. Louis Post-Dispatch, relayed snapshot {snap.group(1)}" if snap else "via St. Louis Post-Dispatch"
    b = BeautifulSoup(html, "html.parser")
    out = []
    for d in b.select("div.race"):
        h = d.find("h3")
        raw = h.get_text(" ", strip=True) if h else ""
        title = TITLE_MAP.get(raw)
        if not title:
            continue
        p = d.select_one("p.precincts")
        ptxt = re.sub(r"\s+", " ", p.get_text(" ", strip=True)) if p else ""
        cands = []
        for tr in d.select("tr[data-name]"):
            n, v = tr.select_one("td.name"), tr.select_one("td.votes")
            if not n or not v:
                continue
            nm = re.sub(r"[\u205f\s]+", " ", n.get_text(" ", strip=True)).strip()
            pm = re.match(r"^(.*?)\s*\(([A-Za-z]+)\)$", nm)
            name, pty = (pm.group(1), party(pm.group(2)) if len(pm.group(2)) > 1 else pm.group(2).upper()) if pm else (nm, "")
            if name.lower().startswith("yes"): name = "Yes"
            elif name.lower().startswith("no"): name = "No"
            cands.append({"name": name, "party": pty, "votes": int(re.sub(r"\D", "", v.get_text()) or 0)})
        m = re.search(r"(\d+)\s+of\s+(\d+)\s+(?:precincts|polling)", ptxt, re.I)
        rr = {"raw_title": raw, "title": title, "category": src.get("category") or "county_stl", "district": None,
              "state": "MO", "county": src.get("county"),
              "reporting_pct": round(100 * int(m.group(1)) / max(1, int(m.group(2))), 1) if m else None,
              "reporting_text": (f"{m.group(1)} of {m.group(2)} precincts" if m else (ptxt.split("•")[0].strip() or "Partial")) + f" ({via})",
              "candidates": cands, "is_measure": any(c["name"] in ("Yes", "No") for c in cands)}
        dm = re.search(r"District (\d+)", raw)
        if dm: rr["district"] = int(dm.group(1))
        out.append(finalize(rr))
    if not out:
        raise RuntimeError("stltoday page fetched but no mapped St. Louis County contests found (layout changed?)")
    return out
