"""Pre-election polling (NEVER mixed with results). Source chain per Earl: RCP -> Silver Bulletin -> Politico -> 270toWin.
Each source is tried once per refresh; a blocked/paywalled source is skipped and reported in polls.json 'source_status'.
Tested 2026-10-21 from this box: RCP 403 (DataDome bot wall), Silver Bulletin averages are paywalled, Politico 403,
270toWin 200 (robots.txt allows; Content-Signal use=reference). Cached for ttl_hours to stay polite."""
import json, os, re, time, datetime
from .common import fetch, ROOT

STATES = {"AL":"alabama","AK":"alaska","AZ":"arizona","AR":"arkansas","CA":"california","CO":"colorado","CT":"connecticut","DE":"delaware","FL":"florida",
 "GA":"georgia","HI":"hawaii","ID":"idaho","IL":"illinois","IN":"indiana","IA":"iowa","KS":"kansas","KY":"kentucky","LA":"louisiana","ME":"maine","MD":"maryland",
 "MA":"massachusetts","MI":"michigan","MN":"minnesota","MS":"mississippi","MO":"missouri","MT":"montana","NE":"nebraska","NV":"nevada","NH":"new-hampshire",
 "NJ":"new-jersey","NM":"new-mexico","NY":"new-york","NC":"north-carolina","ND":"north-dakota","OH":"ohio","OK":"oklahoma","OR":"oregon","PA":"pennsylvania",
 "RI":"rhode-island","SC":"south-carolina","SD":"south-dakota","TN":"tennessee","TX":"texas","UT":"utah","VT":"vermont","VA":"virginia","WA":"washington",
 "WV":"west-virginia","WI":"wisconsin","WY":"wyoming"}
COLOR = {"3e5a96": "D", "244999": "D", "c23237": "R", "b22234": "R"}
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def _probe(url):
    try:
        t = fetch(url, timeout=20)
        if "captcha-delivery" in t or len(t) < 2000: return "blocked (bot wall / empty page)"
        if re.search(r"∙ Paid|paywall|subscribe to read", t, re.I): return "paywalled"
        return "ok"
    except Exception as e:
        return f"blocked ({type(e).__name__}: {str(e)[:80]})"

def _pct(s):
    m = re.search(r"([\d.]+)%", s or ""); return float(m.group(1)) if m else None

def parse_270(html, url):
    from bs4 import BeautifulSoup
    s = BeautifulSoup(html, "html.parser"); t = s.find("table", id="polls")
    if not t: return None
    heads = t.find_all("th", class_="can_name")
    cands = []
    for h in heads:
        col = re.search(r"#([0-9a-fA-F]{6})", h.get("style", "")); p = COLOR.get(col.group(1).lower(), "I") if col else "I"
        cands.append({"name": h.get_text(strip=True), "party": p, "cid": h.get("candidate_id")})
    def row(tr):
        vals = {c["cid"]: _pct(td.get_text()) for c in cands for td in tr.find_all("td", attrs={"candidate_id": c["cid"]})}
        return vals
    out = {"source": "270toWin", "source_url": url, "candidates": [{"name": c["name"], "party": c["party"]} for c in cands]}
    avg = t.find("tr", id="poll_avg_row")
    if avg:
        tds = avg.find_all("td")
        vals = [_pct(td.get_text()) for td in tds[1:1 + len(cands)]]
        out["avg"] = {"label": tds[0].get_text(" ", strip=True), "values": vals}
    first = t.find("tr", class_="poll_row")
    if first:
        v = row(first)
        out["latest"] = {"pollster": first.find("td", class_="poll_src").get_text(" ", strip=True),
                         "date": first.find("td", class_="poll_date").get_text(strip=True),
                         "sample": (first.find("td", class_="poll_sample") or first).get_text(" ", strip=True),
                         "values": [v.get(c["cid"]) for c in cands]}
    for k in ("avg", "latest"):
        if k in out: out[k]["margin"] = margin(out["candidates"], out[k]["values"])
    if all(out.get(k, {}).get("margin") is None for k in ("avg", "latest")): return None  # primary-only / no R-vs-D data
    return out

def margin(cands, vals):
    """Signed R-minus-D margin (positive = R lead) using the leading R and leading D (or leading non-R, e.g. NE independent).
    None for same-party (primary) tables."""
    R = [v for c, v in zip(cands, vals) if c["party"] == "R" and v is not None]
    D = [v for c, v in zip(cands, vals) if c["party"] == "D" and v is not None] or [v for c, v in zip(cands, vals) if c["party"] != "R" and v is not None]
    return round(max(R) - max(D), 1) if R and D else None

def refresh(cfg, races, out_path):
    pc = cfg.get("polls", {})
    if not pc.get("enabled", True): return {}
    prev = json.load(open(out_path)) if os.path.exists(out_path) else {}
    if prev.get("fetched_at"):
        age = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(prev["fetched_at"])).total_seconds()
        if age < pc.get("ttl_hours", 6) * 3600: return prev
    status = {"RCP": _probe(pc.get("rcp_probe_url", "https://www.realclearpolling.com/latest-polls/senate")),
              "Silver Bulletin": _probe(pc.get("silver_probe_url", "https://www.natesilver.net/p/nate-silver-2026-midterm-election-senate-model")),
              "Politico": _probe(pc.get("politico_probe_url", "https://www.politico.com/2026-election/polls/"))}
    # Only 270toWin has a parser today; if RCP/SB/Politico ever return 'ok', add a parser and put it first.
    year = cfg.get("election_date", "2026")[:4]
    res = {}
    for r in races:
        if r.get("level") != "national" or r["category"] not in ("senate", "governor"): continue
        slug = STATES.get(r["state"]); 
        if not slug: continue
        url = f"https://www.270towin.com/{year}-{r['category']}-polls/{slug}"
        try:
            p = parse_270(fetch(url, timeout=20), url)
            if p: p["fetched_at"] = now(); res[r["race_id"]] = p
        except Exception:
            pass
        time.sleep(pc.get("delay_s", 2))
    status["270toWin"] = f"ok ({len(res)} races)"
    doc = {"fetched_at": now(), "label": "PRE-ELECTION POLLING - not results", "source_status": status, "races": res}
    json.dump(doc, open(out_path, "w"), indent=1)
    return doc
