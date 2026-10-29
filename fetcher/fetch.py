"""Run all enabled sources once, normalize, and write site/data/results.json.
Usage: python3 -m fetcher.fetch [--config config.json] [--out site/data/results.json] [--loop SECONDS]
A failing source never breaks the page: its last good data is kept and marked stale with the error message."""
import json, os, re, sys, time, argparse, traceback, datetime
from .adapters import ADAPTERS
from .common import ROOT

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def tally(races, baselines):
    out = {}
    for ch, b in baselines.items():
        t = {"called": {"R": b["R"], "D": b["D"], "O": b.get("O", 0)}, "leading": {"R": 0, "D": 0, "O": 0}, "too_early": 0,
             "holdover": {"R": b["R"], "D": b["D"]}, **{k: v for k, v in b.items() if k not in ("R", "D")}}
        for r in races:
            # scope "mo": Missouri chambers (mo_house / mo_senate) counted from the MO cards; else national races only
            if (r.get("level") == "national") == (b.get("scope") == "mo") or r["category"] != ch: continue
            if r["status"] in ("called", "certified"):
                w = next((c for c in r["candidates"] if c.get("winner")), None)
                p = w["party"] if w else "O"; t["called"][p if p in "RD" else "O"] += 1
            elif r["status"] == "leading":
                p = r["candidates"][0]["party"]; t["leading"][p if p in "RD" else "O"] += 1
            else: t["too_early"] += 1
        out[ch] = t
    return out

def _last(n): return (n or "").replace(",", " ").split()[-1].lower() if (n or "").split() else ""

def merge_feeds(races):
    """State feeds supply live vote counts; the calls sheet supplies calls/key flags. Never mark called from a feed."""
    from .common import finalize
    nat = {r.get("race_id"): r for r in races if r.get("level") == "national" and r.get("race_id")}
    out = [r for r in races if r.get("level") != "state_feed"]
    for f in (r for r in races if r.get("level") == "state_feed"):
        n = nat.get(f["race_id"])
        if n is None:
            f["level"] = "national"; f["title"] += " (state feed only)"; out.append(f); continue
        won = {_last(c["name"]) for c in n["candidates"] if c.get("winner")}
        wonp = {c["party"] for c in n["candidates"] if c.get("winner")}
        cands = [dict(c) for c in f["candidates"]]
        for c in cands:
            c["winner"] = bool(won) and (_last(c["name"]) in won or (not any(_last(x["name"]) in won for x in cands) and c["party"] in wonp))
        n.update(candidates=cands, reporting_pct=f["reporting_pct"], reporting_text=f["reporting_text"],
                 votes_source=f["source_id"], feed_contest=f.get("feed_contest"))
        finalize(n)
        if n.get("called_by") and any(c["winner"] for c in cands): n["status"] = "called"
    return out

def _norm_last(n):
    import unicodedata
    n = unicodedata.normalize("NFKD", n or "").encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\(.*?\)|\*|\b(jr|sr|ii|iii|iv)\b\.?", " ", n)
    w = re.findall(r"[a-z'-]+", n)
    return w[-1].replace("'", "") if w else ""

def add_national_candidates(races, cfg, cfg_path):
    """Fill national races with certified candidates (elections/<date>/national_candidates.json, keyed by race_id).
    Sheet/feed rows always win: a placeholder candidate is only added if no existing row has the same normalized last
    name; matching rows keep their numbers and just gain the incumbent flag."""
    from .common import finalize
    path = os.path.join(ROOT, cfg.get("national_candidates_file") or os.path.join(os.path.dirname(cfg_path), "national_candidates.json"))
    if not os.path.exists(path): return races
    try: nc = json.load(open(path)).get("races", {})
    except Exception as e:
        print("NATIONAL CANDIDATES FAILED", e, file=sys.stderr); return races
    for r in races:
        if r.get("level") != "national": continue
        p = nc.get(r.get("race_id"))
        if not p: continue
        if p.get("note") and not r.get("candidates_note"): r["candidates_note"] = p["note"]
        if p.get("source"): r["candidates_source"] = p["source"]
        full = lambda n: re.sub(r"[^a-z]", "", (n or "").lower())
        have_full = {full(c["name"]): c for c in r["candidates"]}
        have = {_norm_last(c["name"]): c for c in r["candidates"]}
        lastn = [_norm_last(c["name"]) for c in p.get("candidates", [])]
        added = False
        for c in p.get("candidates", []):
            m = have_full.get(full(c["name"]))
            ln = _norm_last(c["name"])
            if m is None and lastn.count(ln) == 1: m = have.get(ln)
            elif m is None:  # two placeholder candidates share a last name: match on first initial
                same = [x for x in r["candidates"] if _norm_last(x["name"]) == ln]
                fi = (c["name"].strip()[:1] or "").lower()
                m = next((x for x in same if len(x["name"].split()) > 1 and x["name"].strip()[:1].lower() == fi), None)
                if m is None and any(len(x["name"].split()) == 1 for x in same): continue  # ambiguous bare last name: don't duplicate
            if m:
                if c.get("incumbent"): m["incumbent"] = True
                if not m.get("party"): m["party"] = c.get("party", "")
            else:
                r["candidates"].append(dict(c, votes=0, winner=False)); added = True
        if not r.get("total_votes") and not r.get("reporting_pct"):
            r["reporting_pct"] = 0; r["reporting_text"] = "No results yet"
        if added:
            st = r.get("status"); finalize(r)
            if st in ("called", "certified"): r["status"] = st
    return races

def add_placeholders(races, cfg, cfg_path):
    """Add a too_early, 0-vote card for every placeholder race (elections/<date>/mo_placeholders.json) that has no live
    race with the same identity (same title, or same category+district). A live race always replaces its placeholder."""
    from .common import finalize
    path = cfg.get("placeholders_file") or os.path.join(os.path.dirname(cfg_path), "mo_placeholders.json")
    path = os.path.join(ROOT, path)
    if not os.path.exists(path): return races
    try: ph = json.load(open(path)).get("races", [])
    except Exception as e:
        print("PLACEHOLDERS FAILED", e, file=sys.stderr); return races
    live = [r for r in races if r.get("level") != "national"]
    titles = {r.get("title") for r in live}
    dists = {(r.get("category"), r.get("district")) for r in live if r.get("district") is not None}
    out = list(races)
    for p in ph:
        if p["title"] in titles: continue
        if p["category"].startswith("county"):
            # county races: same county tab + optional "match" regex on the live contest title (office + district)
            pats = [re.compile(x, re.I) for x in p.get("match", [])]
            if any(r.get("category") == p["category"] and any(x.search(r.get("raw_title", "") + " | " + r.get("title", "")) for x in pats) for r in live): continue
        elif p.get("district") is not None and (p["category"], p["district"]) in dists: continue
        r = {"raw_title": p["title"], "title": p["title"], "category": p["category"], "district": p.get("district"), "state": "MO",
             "level": "county" if p["category"].startswith("county") else "missouri", "source_id": "placeholder",
             "county": p.get("county"), "id": "placeholder:" + p["title"], "placeholder": True,
             "is_measure": bool(p.get("is_measure")), "reporting_pct": 0, "reporting_text": "No results yet",
             "candidates": [dict(c, votes=0) for c in p.get("candidates", [])]}
        for k in ("description", "note", "candidates_source"):
            if p.get(k): r[k] = p[k]
        finalize(r); r["status"] = "too_early"
        out.append(r)
    return out

def run(cfg_path, out_path):
    cfg = json.load(open(os.path.join(ROOT, cfg_path)))
    prev = {}
    if os.path.exists(out_path):
        try: prev = json.load(open(out_path))
        except Exception: prev = {}
    prev_src = {s["id"]: s for s in prev.get("sources", [])}
    sources, races = [], []
    for s in cfg["sources"]:
        if not s.get("enabled", True): continue
        start = s.get("active_from_utc") or (cfg.get("live_start_utc") if s.get("live_only") else None)
        if start and datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(start.replace("Z", "+00:00")):
            sources.append({"id": s["id"], "name": s["name"], "url": s.get("url") or (s.get("urls") or [""])[0], "ok": True, "waiting": True,
                            "checked_at": now(), "updated_at": None, "race_count": 0, "error": None,
                            "note": f"Not polled until {start} (results not published yet)"})
            continue
        meta = {"id": s["id"], "name": s["name"], "url": s.get("url") or (s.get("urls") or [""])[0], "note": s.get("note", ""), "checked_at": now()}
        try:
            try:
                rs = ADAPTERS[s["adapter"]](s)
            except Exception as e1:
                if not s.get("fallback_url"): raise
                rs = ADAPTERS[s["adapter"]](dict(s, url=s["fallback_url"]))
                meta["note"] = f"Primary failed ({type(e1).__name__}: {str(e1)[:120]}); using fallback {s['fallback_url']}"
            for r in rs:
                r["source_id"] = s["id"]; r.setdefault("level", "county" if r["category"].startswith("county") else "missouri")
                r["highlight"] = r["title"] in cfg.get("highlight", [])
                r["id"] = f'{s["id"]}:{r["raw_title"]}'
            meta.update(ok=True, updated_at=now(), race_count=len(rs), error=None)
        except Exception as e:
            p = prev_src.get(s["id"], {})
            rs = [r for r in prev.get("races", []) if r.get("source_id") == s["id"]]
            for r in rs: r["stale"] = True
            meta.update(ok=False, updated_at=p.get("updated_at"), race_count=len(rs), error=f"{type(e).__name__}: {e}"[:300])
            print("SOURCE FAILED", s["id"], meta["error"], file=sys.stderr)
        sources.append(meta); races.extend(rs)
    races = merge_feeds(races)
    races = add_national_candidates(races, cfg, cfg_path)
    races = add_placeholders(races, cfg, cfg_path)
    if any(r.get("source_id") == "placeholder" for r in races):
        sources.append({"id": "placeholder", "name": "Pre-election ballot list (no results yet; see each card for its source)", "url": "https://ballotpedia.org/Missouri_elections,_2026",
                        "ok": True, "checked_at": now(), "updated_at": now(), "race_count": sum(r.get("source_id") == "placeholder" for r in races),
                        "error": None, "note": "Placeholder cards; replaced by Missouri SOS results when they appear."})
    keys = set(cfg.get("key_races", []) + cfg.get("highlight", []))
    for r in races:
        r["key"] = bool(r.get("key") or r["title"] in keys or r.get("race_id") in keys)
        r["highlight"] = r["key"]
        if str(r.get("race_id", "")).upper().startswith(("SAMPLE", "TEST")): r["sample"] = True
    polls = {}
    if cfg.get("polls", {}).get("enabled"):
        try:
            from .polls import refresh
            polls = refresh(cfg, races, os.path.join(os.path.dirname(out_path), "polls.json"))
        except Exception as e:
            print("POLLS FAILED", e, file=sys.stderr)
    mp = {}
    try:
        mp = json.load(open(os.path.join(ROOT, cfg.get("manual_polls_file", "")))).get("races", {}) if cfg.get("manual_polls_file") else {}
    except Exception as e:
        print("MANUAL POLLS FAILED", e, file=sys.stderr)
    for r in races:
        p = polls.get("races", {}).get(r.get("race_id")) or mp.get(r.get("title"))
        if p: r["poll"] = p
    doc = {"social": cfg.get("social", {}),
           "polls_meta": {k: v for k, v in polls.items() if k != "races"},
           "election": cfg["election"], "election_date": cfg.get("election_date"), "preview_banner": cfg.get("preview_banner", ""), "generated_at": now(), "sources": sources, "tallies": tally(races, cfg.get("baselines", {})), "races": races,
           "measures": json.load(open(os.path.join(ROOT, cfg["measures_file"]))).get("measures", []) if cfg.get("measures_file") else []}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"; json.dump(doc, open(tmp, "w"), separators=(",", ":")); os.replace(tmp, out_path)
    try:
        from .chatter import refresh as chatter_refresh
        chatter_refresh(cfg, os.path.join(os.path.dirname(out_path), "chatter.json"))
    except Exception as e:
        print("CHATTER FAILED", e, file=sys.stderr)
    print(f"wrote {out_path}: {len(races)} races; " + ", ".join(f'{s["id"]}={"ok" if s["ok"] else "FAIL"}' for s in sources))
    return doc

if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--config", default=open(os.path.join(ROOT, "elections/ACTIVE")).read().strip())
    a.add_argument("--out", default=os.path.join(ROOT, "site/data/results.json")); a.add_argument("--loop", type=int, default=0)
    o = a.parse_args()
    while True:
        run(o.config, o.out)
        if not o.loop: break
        time.sleep(max(60, o.loop))  # never poll faster than once a minute
