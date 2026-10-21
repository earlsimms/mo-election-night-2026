"""Run all enabled sources once, normalize, and write site/data/results.json.
Usage: python3 -m fetcher.fetch [--config config.json] [--out site/data/results.json] [--loop SECONDS]
A failing source never breaks the page: its last good data is kept and marked stale with the error message."""
import json, os, sys, time, argparse, traceback, datetime
from .adapters import ADAPTERS
from .common import ROOT

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def tally(races, baselines):
    out = {}
    for ch, b in baselines.items():
        t = {"called": {"R": b["R"], "D": b["D"], "O": 0}, "leading": {"R": 0, "D": 0, "O": 0}, "too_early": 0,
             "holdover": {"R": b["R"], "D": b["D"]}, **{k: v for k, v in b.items() if k not in ("R", "D")}}
        for r in races:
            if r.get("level") != "national" or r["category"] != ch: continue
            if r["status"] in ("called", "certified"):
                w = next((c for c in r["candidates"] if c.get("winner")), None)
                p = w["party"] if w else "O"; t["called"][p if p in "RD" else "O"] += 1
            elif r["status"] == "leading":
                p = r["candidates"][0]["party"]; t["leading"][p if p in "RD" else "O"] += 1
            else: t["too_early"] += 1
        out[ch] = t
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
        meta = {"id": s["id"], "name": s["name"], "url": s["url"], "note": s.get("note", ""), "checked_at": now()}
        try:
            rs = ADAPTERS[s["adapter"]](s)
            for r in rs:
                r["source_id"] = s["id"]; r.setdefault("level", "missouri" if r["category"] != "county" else "county")
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
    doc = {"election": cfg["election"], "election_date": cfg.get("election_date"), "preview_banner": cfg.get("preview_banner", ""), "generated_at": now(), "sources": sources, "tallies": tally(races, cfg.get("baselines", {})), "races": races,
           "measures": json.load(open(os.path.join(ROOT, cfg["measures_file"]))).get("measures", []) if cfg.get("measures_file") else []}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"; json.dump(doc, open(tmp, "w"), separators=(",", ":")); os.replace(tmp, out_path)
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
