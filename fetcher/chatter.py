"""Pull X list timelines server-side (syndication endpoint) into site/data/chatter.json.
Never raises; on failure a list keeps its previous posts."""
import datetime, email.utils, html, json, os, re, sys, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
SYND = "https://syndication.twitter.com/srv/timeline-list/screen-name/{owner}/slug/{slug}"
MAX = 50

def _now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def _owner_slug(url):
    m = re.search(r"x\.com/([^/]+)/lists/([^/?#]+)", url or "") or re.search(r"twitter\.com/([^/]+)/lists/([^/?#]+)", url or "")
    return (m.group(1), m.group(2)) if m else (None, None)

def _iso(s):
    try: return email.utils.parsedate_to_datetime(s).astimezone(datetime.timezone.utc).isoformat(timespec="seconds")
    except Exception: return s

def _text(t):
    txt = t.get("full_text") or t.get("text") or ""
    ents = t.get("entities") or {}
    for u in ents.get("urls", []) or []:
        if u.get("url"): txt = txt.replace(u["url"], u.get("expanded_url") or u["url"])
    for m in (ents.get("media", []) or []) + ((t.get("extended_entities") or {}).get("media", []) or []):
        if m.get("url"): txt = txt.replace(m["url"], "")
    return html.unescape(txt).strip()

def _post(t):
    rt = t.get("retweeted_status")
    src = rt or t
    u, ru = (src.get("user") or {}), (t.get("user") or {})
    pid = src.get("id_str") or str(src.get("id", ""))
    h = u.get("screen_name", "")
    return {"id": pid, "name": u.get("name", h), "handle": h, "avatar": u.get("profile_image_url_https", ""),
            "text": _text(src), "created_at": _iso(t.get("created_at", "")), "url": f"https://x.com/{h}/status/{pid}",
            "retweet": bool(rt), "retweeted_by": ru.get("screen_name") if rt else None}

def fetch_list(owner, slug, timeout=25):
    req = urllib.request.Request(SYND.format(owner=owner, slug=slug), headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"})
    body = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', body, re.S)
    if not m: raise ValueError("no __NEXT_DATA__ (rate-limited?)")
    entries = json.loads(m.group(1))["props"]["pageProps"]["timeline"]["entries"]
    posts = [_post(e["content"]["tweet"]) for e in entries if (e.get("content") or {}).get("tweet")]
    if not posts: raise ValueError("timeline empty (rate-limited?)")
    posts.sort(key=lambda p: p["created_at"], reverse=True)
    return posts[:MAX]

def refresh(cfg, out_path):
    try:
        prev = {}
        try: prev = {l.get("name"): l for l in json.load(open(out_path)).get("lists", [])}
        except Exception: pass
        lists = []
        for L in (cfg.get("social") or {}).get("x_lists", []):
            if L.get("link_only"): continue
            owner, slug = _owner_slug(L.get("url"))
            p = prev.get(L["name"], {})
            ent = {"name": L["name"], "id": L.get("id"), "url": L.get("url") or f"https://x.com/i/lists/{L.get('id')}", "checked_at": _now()}
            try:
                if not slug: raise ValueError("cannot derive slug from url")
                ent.update(posts=fetch_list(owner, slug), fetched_at=_now(), ok=True, error=None)
            except Exception as e:
                ent.update(posts=p.get("posts", []), fetched_at=p.get("fetched_at"), ok=False, error=f"{type(e).__name__}: {e}"[:200])
                print("CHATTER FAILED", L["name"], ent["error"], file=sys.stderr)
            lists.append(ent)
        doc = {"generated_at": _now(), "lists": lists}
        tmp = out_path + ".tmp"; json.dump(doc, open(tmp, "w"), separators=(",", ":"), ensure_ascii=False); os.replace(tmp, out_path)
        print("wrote chatter: " + ", ".join(f'{l["name"]}={len(l["posts"])}{"" if l["ok"] else " (stale)"}' for l in lists))
    except Exception as e:
        print("CHATTER STEP FAILED", e, file=sys.stderr)
