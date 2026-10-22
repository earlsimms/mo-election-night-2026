"""LiveVoterTurnout ENR pages (used by St. Charles County). VERIFIED against the Aug 4 2026 primary page.
Each contest: <span id="raceHeading_N">Contest: TITLE, VOTE FOR 1, Precincts Reported: a of b (p%)</span> followed by
<td data-candidate data-race=N>, <td data-winner>, <td data-votes>. A non-empty data-winner cell = source-declared winner."""
import re
from bs4 import BeautifulSoup
from ..common import fetch, classify, finalize, split_party

def parse(src):
    s = BeautifulSoup(fetch(src["url"]), "html.parser")
    final = bool(re.search(r"Official Final", s.get_text(" ")[:5000]))
    out = []
    for h in s.find_all("span", id=re.compile(r"^raceHeading_\d+$")):
        rid = h["id"].split("_")[1]
        m = re.match(r"Contest:\s*(.*?),\s*VOTE FOR.*?Reported:\s*(\d+) of (\d+)", h.get_text(" ", strip=True))
        if not m: continue
        title, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        box = h.find_parent(class_="container-box")
        cands = []
        for td in box.find_all("td", attrs={"data-candidate": "true", "data-race": rid}):
            cid = td["data-contestant"]
            nm, p = split_party(td.find("span").get_text(strip=True))
            v = box.find("td", attrs={"data-contestant": cid, "data-votes": "true"})
            w = box.find("td", attrs={"data-contestant": cid, "data-winner": "true"})
            if nm.upper() == "NO CANDIDATE FILED": continue
            cands.append({"name": nm.title(), "party": p, "votes": int(re.sub(r"\D", "", v.get_text()) or 0),
                          "winner": bool(w and (w.get_text(strip=True) or w.find(["img", "i", "span"])))})
        cat, label, dist = classify(title, county=src.get("county"))
        if cat != "county": label = f"{src['county']}: {label}"
        ptag = re.search(r"\((REPUBLICAN|DEMOCRATIC|LIBERTARIAN|GREEN)", " ".join(c["name"] for c in cands).upper())
        out.append(finalize({"raw_title": title, "title": label, "category": src.get("category") or "county", "district": dist, "state": "MO",
                             "county": src.get("county"), "reporting_pct": round(100 * a / b, 1) if b else None,
                             "reporting_text": f"{a} of {b} precincts", "candidates": cands,
                             "is_measure": any(c["name"].upper() in ("YES", "NO") for c in cands)}, official=final))
    return out
