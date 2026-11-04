"""Decision Desk HQ race calls: the ONLY call source for the dashboard.
Reads @DecisionDeskHQ's recent posts server-side (syndication endpoint, no API key), parses projection posts, merges them
into site/data/ddhq_calls.json (accumulated across runs; seeded from the live site if missing), and applies a call only
when the race AND candidate match unambiguously. Unmatched/ambiguous call posts go to site/data/ddhq_unmatched.json.
Never raises."""
import datetime, html, json, os, re, sys, unicodedata, urllib.request
from .chatter import UA, _post

SYND = "https://syndication.twitter.com/srv/timeline-profile/screen-name/DecisionDeskHQ"
SEED = "https://earlsimms.github.io/mo-election-night-2026/data/ddhq_calls.json"
STATES = {"alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY"}
CODES = set(STATES.values())
PARTY = {"R": "R", "D": "D", "I": "I", "L": "L", "G": "G", "REP": "R", "DEM": "D", "IND": "I", "LIB": "L"}

def _now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def _ascii(s): return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()

def _last(n):
    n = _ascii(n).lower()
    n = re.sub(r"\(.*?\)|\*|\b(jr|sr|ii|iii|iv)\b\.?", " ", n)
    w = re.findall(r"[a-z'-]+", n)
    return w[-1].replace("'", "") if w else ""

# "Decision Desk HQ projects Wesley Bell wins the election for US House in Missouri's 1st Congressional District. #DecisionMade: 10:07pm ET"
# "DDHQ PROJECTION: Josh Hawley (R) wins MO-SEN" / "Decision Desk HQ projects Mike Kehoe (R) has won the race for Governor of Missouri."
PROJ = re.compile(r"(?:Decision\s*Desk\s*HQ|DDHQ)\s*(?:projection|projects?|race\s*call|calls?)\b\s*[:\-–]*\s*(?:that\s+)?", re.I)
WIN = re.compile(r"^(?P<who>[A-Z][\w.'’\- ]{1,60}?)\s*(?:\((?P<party>[A-Za-z]{1,3})(?:[-–][A-Z]{2})?\)\s*)?(?:,\s*)?(?:wins|will win|has won|won|is projected to win|defeats\s+[\w.'’\- ]+?\s*(?:\([A-Za-z]{1,3}\)\s*)?(?:in|for)?)\s+(?P<rest>.*)$", re.I | re.S)
MEAS = re.compile(r"(?:(?P<yn>yes|no)\s+(?:wins|prevails)\s+(?:on|for)\s+)?(?:the\s+)?(?P<st>Missouri\s+|MO\s+)?(?P<m>(?:Constitutional\s+)?Amendment\s+(?:No\.\s*)?\d+|Proposition\s+[A-Z0-9]+|Prop\.?\s+[A-Z0-9]+)\b(?P<after>[^.#\n]*)", re.I)
PASS = re.compile(r"\b(passes|passed|will pass|is approved|approved|is adopted|adopted|yes wins)\b", re.I)
FAIL = re.compile(r"\b(fails|failed|will fail|is rejected|rejected|is defeated|defeated|no wins)\b", re.I)

def _district(s):
    m = re.search(r"\b(\d{1,3})(?:st|nd|rd|th)?\s+(?:Congressional\s+|State\s+Senate\s+|State\s+House\s+|Senate\s+|House\s+|Legislative\s+)?District\b", s, re.I) \
        or re.search(r"\bDistrict\s+(?:No\.\s*)?(\d{1,3})\b", s, re.I) or re.search(r"\b[A-Z]{2}-(\d{1,2})\b", s)
    if m: return str(int(m.group(1)))
    if re.search(r"at[- ]large|\b[A-Z]{2}-AL\b", s, re.I): return "AL"
    return None

def _state(s):
    a = _ascii(s).lower()
    hits = {c for n, c in STATES.items() if re.search(r"\b" + n + r"\b", a)}
    if "west virginia" in a: hits.discard("VA")
    if re.search(r"\bwashington,? d\.?c\b", a): hits.discard("WA")
    for k in ("north ", "south ", "new ", "west "):
        pass
    # drop states that are substrings of a longer matched name (Virginia inside West Virginia handled above; Kansas in Arkansas)
    if "AR" in hits and not re.search(r"\bkansas\b", a.replace("arkansas", "")): hits.discard("KS")
    code = re.findall(r"\b([A-Z]{2})-(?:\d{1,2}|AL|SEN|GOV|Sen|Gov)\b", s)
    hits |= {c for c in code if c in CODES}
    return hits.pop() if len(hits) == 1 else None

def _office(s):
    u = s.lower()
    if re.search(r"\bstate\s+senate\b|\bmissouri\s+senate\b|\bstate\s+senator\b", u): return "mo_senate"
    if re.search(r"\bstate\s+house\b|\bstate\s+representative\b|\bhouse\s+of\s+representatives\b(?!.*congress)|\bmissouri\s+house\b", u) and "u.s." not in u and "us house" not in u: return "mo_house"
    if re.search(r"\bstate\s+auditor\b", u): return "mo_statewide:State Auditor"
    if re.search(r"\bgovernor\b|\bgubernatorial\b|-gov\b", u) and "lieutenant" not in u and "lt." not in u: return "governor"
    if re.search(r"\bu\.?\s?s\.?\s+senate\b|\bsenate\b|-sen\b", u): return "senate"
    if re.search(r"\bu\.?\s?s\.?\s+house\b|\bcongress|\bhouse\b|\b[a-z]{2}-(\d{1,2}|al)\b", u): return "house"
    return None

def parse(text):
    """Return a list of call dicts found in one post's text (usually 0 or 1)."""
    t = html.unescape(text or "").replace("’", "'").replace("\u00a0", " ")
    m = PROJ.search(t)
    if not m: return []
    body = re.split(r"#DecisionMade|\n\s*\n|Follow live|https?://", t[m.end():], 1)[0].strip()
    if re.search(r"\bprimary\b|\bnominat", body, re.I): return []  # general-election night only
    if re.search(r"\b(control|majority)\b", body, re.I) and not re.search(r"\bdistrict\b", body, re.I): return []  # chamber-control calls are not race calls
    mm = MEAS.search(body)
    if mm and not WIN.match(body):
        after = mm.group("after") or ""
        yn = (mm.group("yn") or "").lower()
        res = "pass" if yn == "yes" or PASS.search(after) else "fail" if yn == "no" or FAIL.search(after) else None
        if not res: return []
        st = "MO" if mm.group("st") or re.search(r"\bmissouri\b", body, re.I) else _state(body)
        num = re.sub(r"(?i)^(constitutional\s+)?amendment\s+(no\.\s*)?", "Amendment ", mm.group("m"))
        num = re.sub(r"(?i)^prop(osition|\.)?\s+", "Proposition ", num).strip()
        return [{"kind": "measure", "state": st, "measure": num.title().replace("Proposition", "Proposition"), "result": res}]
    w = WIN.match(body)
    if not w: return []
    rest = re.split(r"(?<!\b[A-Z])(?<!\bSt)(?<!\bU\.S)\.\s|\.$", w.group("rest").strip(), 1)[0]
    rest = re.sub(r"(?i)^(the\s+)?(general\s+)?(election|race|seat|contest)?\s*(for|in|to)?\s*", "", rest)
    p = (w.group("party") or "").upper()
    return [{"kind": "candidate", "candidate": w.group("who").strip(), "party": PARTY.get(p, p[:1] if p else ""),
             "office": _office(rest), "state": _state(rest), "district": _district(rest), "where": rest[:160]}]

LAST_STATUS = {"rate_limited": False}

def _get(url, timeout):
    """urllib first; on any failure (e.g. 429 from shared runner IPs) retry once with a browser-TLS client (curl_cffi)."""
    import time, random
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"})
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except Exception as e1:
        if "429" in str(e1): LAST_STATUS["rate_limited"] = True
        time.sleep(2 + random.random() * 3)
        try:
            from curl_cffi import requests as cr
        except Exception:
            raise e1
        r = cr.get(url, impersonate="chrome", timeout=timeout, headers={"Accept-Language": "en-US,en;q=0.9"})
        if r.status_code != 200:
            if r.status_code == 429: LAST_STATUS["rate_limited"] = True
            raise RuntimeError(f"HTTP {r.status_code} (urllib: {e1}; curl_cffi retry also failed)")
        return r.text

def fetch_posts(timeout=25):
    LAST_STATUS["rate_limited"] = False
    body = _get(SYND, timeout)
    LAST_STATUS["rate_limited"] = False
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', body, re.S)
    if not m: raise ValueError("no __NEXT_DATA__ (rate-limited?)")
    entries = json.loads(m.group(1))["props"]["pageProps"]["timeline"]["entries"]
    posts = [_post(e["content"]["tweet"]) for e in entries if (e.get("content") or {}).get("tweet")]
    if not posts: raise ValueError("timeline empty (rate-limited?)")
    return [p for p in posts if p["handle"].lower() == "decisiondeskhq"]  # own posts only (also counts RTs of DDHQ itself)

def _dist_eq(a, b):
    a, b = str(a if a is not None else "").upper().lstrip("0"), str(b if b is not None else "").upper().lstrip("0")
    return a != "" and a == b

def find_races(call, races):
    """Races this call refers to, or (None, reason)."""
    if call["kind"] == "measure":
        if call.get("state") != "MO": return None, "measure not in Missouri"
        hits = [r for r in races if r.get("is_measure") and r.get("state") == "MO" and r.get("level") == "missouri" and r["title"].lower() == call["measure"].lower()]
        return (hits, None) if hits else (None, "no matching Missouri measure card")
    off, st, d = call.get("office"), call.get("state"), call.get("district")
    if not off or not st: return None, f"could not identify office/state (office={off}, state={st})"
    if off in ("senate", "governor"):
        hits = [r for r in races if r.get("level") == "national" and r["category"] == off and r.get("state") == st]
    elif off == "house":
        if not d: return None, "U.S. House call without district"
        hits = [r for r in races if r.get("state") == st and ((r.get("level") == "national" and r["category"] == "house") or r["category"] == "mo_ushouse")
                and _dist_eq(r.get("district"), d)]
        if not hits and d == "AL": hits = [r for r in races if r.get("level") == "national" and r["category"] == "house" and r.get("state") == st and str(r.get("district")).upper() in ("AL", "0", "1")]
    elif off in ("mo_senate", "mo_house"):
        if st != "MO" or not d: return None, "state-legislative call outside Missouri or without district"
        hits = [r for r in races if r["category"] == off and _dist_eq(r.get("district"), d)]
    elif off.startswith("mo_statewide:"):
        hits = [r for r in races if r["category"] == "mo_statewide" and r["title"] == off.split(":", 1)[1] and st == "MO"]
    else: hits = []
    if not hits: return None, "no matching race"
    if off in ("senate",) and len({r.get("race_id") for r in hits}) > 1:
        return None, "more than one Senate race in state (special election?) - ambiguous"
    return hits, None

def _cand(call, race):
    ln = _last(call["candidate"])
    full = re.sub(r"[^a-z]", "", _ascii(call["candidate"]).lower())
    m = [c for c in race["candidates"] if _last(c["name"]) == ln]
    if len(m) > 1: m = [c for c in m if re.sub(r"[^a-z]", "", _ascii(c["name"]).lower()) == full]
    if len(m) != 1: return None
    if call.get("party") and m[0].get("party") and call["party"] != m[0]["party"]: return None
    return m[0]

def strip_calls(races):
    """DDHQ is the only call source: drop winner flags/'called' from sheet and feeds; keep 'certified' (official)."""
    from .common import finalize
    for r in races:
        if r.get("status") == "certified": continue
        if r.get("status") == "called" or any(c.get("winner") for c in r["candidates"]):
            for c in r["candidates"]: c["winner"] = False
            ph = r.get("placeholder"); finalize(r)
            if ph: r["status"] = "too_early"
        r["called_by"] = ""; r.pop("called_url", None)

def _load(path):
    try: return json.load(open(path))
    except Exception: pass
    try:
        req = urllib.request.Request(SEED, headers={"User-Agent": UA})
        return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    except Exception: return {"calls": {}}

def apply(races, out_dir, posts=None):
    """Strip non-DDHQ calls, refresh DDHQ calls, apply them. Returns a source-status dict. Never raises."""
    meta = {"id": "ddhq", "name": "Decision Desk HQ race calls (@DecisionDeskHQ on X)", "url": "https://x.com/DecisionDeskHQ",
            "checked_at": _now(), "note": "All race calls come from Decision Desk HQ projection posts."}
    try:
        strip_calls(races)
        path = os.path.join(out_dir, "ddhq_calls.json")
        store = _load(path); calls = store.get("calls", {})
        try:
            if posts is None: posts = fetch_posts()
            for p in posts:
                for i, c in enumerate(parse(p["text"])):
                    k = f'{p["id"]}:{i}'
                    if k not in calls: calls[k] = dict(c, post_id=p["id"], url=p["url"], created_at=p["created_at"], text=p["text"][:400], seen_at=_now())
            meta.update(ok=True, error=None, updated_at=_now())
        except Exception as e:
            meta.update(ok=False, error=f"{type(e).__name__}: {e}"[:200], updated_at=store.get("fetched_at"))
            print("DDHQ FETCH FAILED", meta["error"], file=sys.stderr)
        unmatched, applied = [], 0
        for k, c in sorted(calls.items(), key=lambda kv: kv[1].get("created_at") or ""):  # later posts override earlier
            hits, why = find_races(c, races)
            if not hits: unmatched.append(dict(c, key=k, reason=why)); continue
            ok = 0
            for r in hits:
                if r.get("status") == "certified": ok += 1; continue
                if c["kind"] == "measure":
                    w = next((x for x in r["candidates"] if x["name"].lower() == ("yes" if c["result"] == "pass" else "no")), None)
                else: w = _cand(c, r)
                if not w: continue
                for x in r["candidates"]: x["winner"] = x is w
                r.update(status="called", called_by="DDHQ", called_url=c["url"], called_at=c.get("created_at")); ok += 1
            if ok: applied += 1
            else: unmatched.append(dict(c, key=k, reason="candidate not found unambiguously on the matching race(s)"))
        if meta.get("ok"): store["fetched_at"] = _now()
        store["calls"] = calls; store["generated_at"] = _now()
        for fn, doc in ((path, store), (os.path.join(out_dir, "ddhq_unmatched.json"), {"generated_at": _now(), "unmatched": unmatched})):
            tmp = fn + ".tmp"; json.dump(doc, open(tmp, "w"), indent=1, ensure_ascii=False); os.replace(tmp, fn)
        meta.update(race_count=applied, note=meta["note"] + f" {len(calls)} call posts stored, {applied} applied, {len(unmatched)} unmatched (see data/ddhq_unmatched.json).")
        print(f"ddhq: {len(calls)} calls, {applied} applied, {len(unmatched)} unmatched" + ("" if meta.get("ok") else " (fetch failed, using stored calls)"))
    except Exception as e:
        meta.update(ok=False, error=f"{type(e).__name__}: {e}"[:200]); print("DDHQ STEP FAILED", e, file=sys.stderr)
    return meta
