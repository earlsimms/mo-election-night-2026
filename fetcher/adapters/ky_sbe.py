"""Kentucky State Board of Elections live results (vrsws.sos.ky.gov/liveresults) - HTML scrape (KY left Clarity).
Only the bare /liveresults/ URL is served to scripts (query strings like ?id=2 get an Akamai 503 or a stale 2026 Primary
page), so we parse the statewide tables on the home page. Votes only; calls come from the national sheet."""
import re, html as H
from .state_feeds import _build, P

def parse_html(t):
    m = re.search(r'electionBodyText"><div>([^<]*)', t)
    if m and "General" not in m.group(1):
        raise RuntimeError(f"KY page shows '{m.group(1)}', not the General election")
    rep = None
    pm = re.search(r'Precincts.*?Participating:\s*</div>\s*<div[^>]*>([\d,]+).*?Reporting:\s*</div>\s*<div[^>]*>([\d,]+)', t, re.S)
    if pm: tot, a = (int(x.replace(",", "")) for x in pm.groups()); rep = (a, tot)
    C = {}
    for blk in re.split(r'class="results-tbl results-tbl', t)[1:]:
        tm = re.search(r'justify-content:flex-end;">\s*([^<]+?)\s*<', blk)
        if not tm: continue
        name = re.sub(r"\s+", " ", H.unescape(tm.group(1))).strip()
        if name in C: continue
        cands = re.findall(r'candidate-name">([^<]+)</div>\s*<div[^>]*candidate-party">([^<]*)</div>.*?candidate-total">([\d,]+)', blk, re.S)
        C[name] = {"rep": rep, "cands": [(H.unescape(n).strip(), P(p), int(v.replace(",", ""))) for n, p, v in cands]}
    return C

def _lu(t):
    import datetime
    m = re.search(r'Last Update: " \+ "([^"]+)', t)
    try: return m.group(1), datetime.datetime.strptime(m.group(1), "%m/%d/%Y %I:%M:%S %p")
    except Exception: return (m.group(1) if m else None), datetime.datetime.min

def parse(src):
    """Akamai edges are flaky (403 for one TLS fingerprint, stale cache for another): try several, keep the freshest."""
    from .mo_sos import _session
    cr = type(_session())  # ensures curl_cffi is installed
    best, errs = None, []
    for imp in ("chrome", "safari", "firefox", "edge"):
        try:
            r = cr(impersonate=imp).get(src["url"], timeout=60)
            if r.status_code != 200 or len(r.text) < 5000: errs.append(f"{imp}:{r.status_code}"); continue
            if best is None or _lu(r.text)[1] > _lu(best)[1]: best = r.text
        except Exception as e: errs.append(f"{imp}:{type(e).__name__}")
    if best is None: raise RuntimeError("KY SBE blocked all fingerprints: " + ", ".join(errs))
    out = _build(src, parse_html(best))
    lu = _lu(best)[0]
    for x in out:
        if lu: x["reporting_text"] += f"; KY SBE last update {lu}"
    return out
