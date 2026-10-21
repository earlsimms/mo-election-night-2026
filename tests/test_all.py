"""python3 tests/test_all.py  -- checks parsers against known official 2024 Missouri numbers and status logic."""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetcher.fetch import run
d = run("elections/preview-2024/config.json", "/tmp/test_results.json"); R = d["races"]
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
check(n["SAMPLE (fake) - TX Senate"]["status"] == "called" and n["SAMPLE (fake) - NC Senate"]["status"] == "leading" and n["SAMPLE (fake) - ME Senate"]["status"] == "too_early", "national status logic")
check(any(r["source_id"] == "stlco" for r in R) and any(r["source_id"] == "stcharles" for r in R), "county adapters parsed live archive pages")
b = next(s for s in d["sources"] if s["id"] == "broken"); check(not b["ok"] and b["error"], "broken source isolated, error reported")
print("measures:", sorted(r["title"] for r in R if r["category"] == "mo_measure"))
pass
# --- state feeds + key races (appended) ---
t = {r["race_id"]: r for r in R if r.get("race_id", "").startswith("TEST")}
ok2 = 0
def chk(c, m):
    global ok2; print(("PASS " if c else "FAIL ") + m); ok2 += (not c)
chk(t["TEST-PA-SEN"]["candidates"][0]["votes"] == 3399295 and t["TEST-PA-SEN"]["status"] == "called", "PA feed votes + sheet call merged (McCormick 3,399,295)")
chk(t["TEST-MN-SEN"]["candidates"][0]["votes"] == 1792441 and t["TEST-MN-SEN"]["status"] != "called", "MN feed Klobuchar 1,792,441, not called without sheet")
chk(t["TEST-FL-SEN"]["candidates"][0]["votes"] == 5977706, "FL feed Rick Scott 5,977,706")
chk(t["TEST-WA-SEN"]["candidates"][0]["votes"] == 2252577, "WA feed Cantwell 2,252,577")
chk(t["TEST-NC-GOV"]["candidates"][0]["name"].startswith("Josh Stein"), "NC feed governor")
chk("TEST-GA-HOUSE-2" in t, "GA feed parsed")
chk(g("MO House 96")["key"] and t["TEST-PA-SEN"]["key"], "key races from config (MO) and race_id")
sys.exit(ok + ok2)
