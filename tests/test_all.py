"""python3 tests/test_all.py  -- checks parsers against known official 2024 Missouri numbers and status logic."""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetcher.fetch import run
d = run("config.test2024.json", "/tmp/test_results.json"); R = d["races"]
def g(t, src="mo_sos"): return next(r for r in R if r["title"] == t and r["source_id"] == src)
ok = 0
def check(c, msg):
    global ok; print(("PASS " if c else "FAIL ") + msg); ok += (not c)
check(g("U.S. Senator (MO)")["candidates"][0]["votes"] == 1651907, "Hawley 1,651,907 (SOS PDF)")
check(g("Governor")["candidates"][0]["name"] == "Mike Kehoe", "Governor Kehoe")
check([c["votes"] for c in g("Amendment 3")["candidates"]] == [1538659, 1443022], "Amendment 3 yes/no 2024")
check(g("Amendment 6")["candidates"][0]["name"] == "No" and g("Amendment 6")["candidates"][0]["votes"] == 1711527, "Amendment 6 (2024) failed 1,711,527 No")
check(len([r for r in R if r["category"] == "mo_ushouse" and r["source_id"] == "mo_sos"]) == 8, "8 MO US House districts")
check(len([r for r in R if r["category"] == "mo_house" and r["source_id"] == "mo_sos"]) == 163, "163 MO House districts")
check(g("MO House 96")["highlight"] and g("MO House 105")["highlight"], "House 96/105 highlighted")
check(len([r for r in R if r["category"] == "mo_measure"]) == 6, "6 statewide measures in 2024 (Am 2,3,5,6,7 + Prop A)")
n = {r["title"]: r for r in R if r["source_id"] == "national"}
check(n["TX Senate"]["status"] == "called" and n["NC Senate"]["status"] == "leading" and n["ME Senate"]["status"] == "too_early", "national status logic")
check(any(r["source_id"] == "stlco" for r in R) and any(r["source_id"] == "stcharles" for r in R), "county adapters parsed live archive pages")
b = next(s for s in d["sources"] if s["id"] == "broken"); check(not b["ok"] and b["error"], "broken source isolated, error reported")
print("measures:", sorted(r["title"] for r in R if r["category"] == "mo_measure"))
sys.exit(ok)
