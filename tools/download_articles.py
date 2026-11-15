"""Crawl the public Encompass help center (Intercom). Respects robots.txt Crawl-delay: 1.
Usage: python -I enc_crawl.py <outdir>
Writes <outdir>/tree.json (collections + article ids) and <outdir>/pages/<id>.json (one per article).
Safe to re-run: already-downloaded articles are skipped.
"""
import json, os, re, sys, time, urllib.request

BASE = "https://help.encompasstech.com/en-us/"
OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, "pages"), exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (compatible; kb-indexer/1.0)"}
last = [0.0]


def get(url):
    for attempt in range(5):
        wait = 1.1 - (time.time() - last[0])
        if wait > 0:
            time.sleep(wait)
        last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        except Exception as e:
            print("retry", attempt, url, e, flush=True)
            time.sleep(3 * (attempt + 1))
    print("FAILED", url, flush=True)
    return None


def next_data(h):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    return json.loads(m.group(1))["props"]["pageProps"]


def art_id(url):
    return re.search(r"/articles/(\d+)", url).group(1)


home = get(BASE)
top = sorted(set(re.findall(r'href="(https://help\.encompasstech\.com/en-us/collections/[^"]+)"', home)))
print("collections:", len(top), flush=True)


def build(c, fetch_if_partial=True):
    node = {"id": c["id"], "n": c["name"], "d": c.get("description") or "", "u": c["url"],
            "a": [], "c": []}
    for s in c.get("articleSummaries") or []:
        node["a"].append({"id": art_id(s["url"]), "t": s["title"], "s": s.get("summary") or "",
                          "u": s["url"], "up": (s.get("lastUpdatedDate") or "")[:10]})
    for sc in c.get("subcollections") or []:
        listed = len(sc.get("articleSummaries") or [])
        nested = sc.get("subcollections") or []
        if fetch_if_partial and (listed < (sc.get("articleCount") or 0) and not nested):
            h = get(sc["url"])
            if h:
                sc = next_data(h)["collection"]
        node["c"].append(build(sc))
    return node


def total(n):
    return len(n["a"]) + sum(total(c) for c in n["c"])


tree = []
for url in top:
    h = get(url)
    if not h:
        continue
    col = next_data(h)["collection"]
    node = build(col)
    node["expected"] = col.get("articleCount")
    tree.append(node)
    print(f'{col["name"]}: {total(node)} listed / {col.get("articleCount")} expected', flush=True)

json.dump(tree, open(os.path.join(OUT, "tree.json"), "w", encoding="utf-8"), ensure_ascii=False)

ids = {}
def collect(n):
    for a in n["a"]:
        ids[a["id"]] = a["u"]
    for c in n["c"]:
        collect(c)
for n in tree:
    collect(n)
print("unique articles:", len(ids), flush=True)

done = 0
for i, (aid, url) in enumerate(sorted(ids.items())):
    path = os.path.join(OUT, "pages", aid + ".json")
    if os.path.exists(path):
        continue
    h = get(url)
    if not h:
        continue
    try:
        pp = next_data(h)
        ac = pp["articleContent"]
        m = re.search(r"<article[^>]*>(.*?)</article>", h, re.S)
        rec = {"id": aid, "t": ac.get("title"), "desc": ac.get("description"), "up": (ac.get("lastUpdatedDate") or "")[:10],
               "u": url, "html": m.group(1) if m else "", "crumbs": [b["name"] for b in pp.get("breadcrumbs") or []]}
        json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        done += 1
    except Exception as e:
        print("parse error", url, e, flush=True)
    if (i + 1) % 50 == 0:
        print(f"articles {i + 1}/{len(ids)}", flush=True)
print("DONE new:", done, "total files:", len(os.listdir(os.path.join(OUT, "pages"))), flush=True)
