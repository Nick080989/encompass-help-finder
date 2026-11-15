"""Build the search index + article bodies for the Encompass Help Finder.
Usage: python -I enc_build.py <crawl_dir> <site_dir>
"""
import json, os, re, sys, html
from html.parser import HTMLParser

CRAWL, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
BASE = "https://help.encompasstech.com"
tree = json.load(open(os.path.join(CRAWL, "tree.json"), encoding="utf-8"))
pages = {}
for f in os.listdir(os.path.join(CRAWL, "pages")):
    r = json.load(open(os.path.join(CRAWL, "pages", f), encoding="utf-8"))
    pages[r["id"]] = r
# Articles listed in a collection whose page could not be downloaded (server error at the source) get a stub.
def _stubs(n):
    for a in n["a"]:
        if a["id"] not in pages:
            pages[a["id"]] = {"id": a["id"], "t": a["t"], "desc": a["s"], "up": a["up"], "u": a["u"], "crumbs": [],
                              "html": "<p><b>The full text of this article was unavailable</b> because the Encompass help center "
                                      "returned a server error when it was downloaded on 14 Nov 2026. Use Open original to try it there.</p>"}
            print("stub:", a["t"])
    for c in n["c"]:
        _stubs(c)
for _n in tree:
    _stubs(_n)
ids = set(pages)

KEEP = {'p', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'b', 'em', 'i', 'code', 'pre', 'table', 'thead',
        'tbody', 'tr', 'td', 'th', 'br', 'blockquote', 'sup', 'sub', 'hr'}
VOID = {'br', 'hr'}


def absu(u):
    if u.startswith('//'): return 'https:' + u
    if u.startswith('/'): return BASE + u
    return u


class San(HTMLParser):
    def __init__(s, art_url):
        super().__init__(convert_charrefs=True)
        s.out, s.stack, s.skip, s.url = [], [], 0, art_url

    def handle_starttag(s, t, attrs):
        a = dict(attrs)
        if t in ('script', 'style', 'svg', 'button', 'nav'):
            s.skip += 1; return
        if s.skip: return
        if t == 'h1': t = 'h2'
        if t in KEEP:
            if t in ('td', 'th'):
                extra = ''.join(f' {k}="{html.escape(a[k])}"' for k in ('colspan', 'rowspan') if a.get(k) and a[k].isdigit())
                s.out.append(f'<{t}{extra}>')
            elif t == 'table':
                s.out.append('<div class="tw"><table>')
            else:
                s.out.append(f'<{t}>')
            if t not in VOID: s.stack.append(t)
        elif t == 'a':
            href = absu(a.get('href') or '')
            m = re.search(r'help\.encompasstech\.com/[a-z-]+/articles/(\d+)', href)
            if re.search(r'intercom-attachments|intercomcdn|intercom-attachments', href):
                s.stack.append('a~')  # wrapper around a screenshot: drop the tag, keep inner content
            elif m and m.group(1) in ids:
                s.out.append(f'<a href="#a-{m.group(1)}" data-int="1">'); s.stack.append('a')
            elif href.startswith('http'):
                s.out.append(f'<a href="{html.escape(href)}" target="_blank" rel="noopener">'); s.stack.append('a')
            else:
                s.stack.append('a~')
        elif t == 'img':
            alt = (a.get('alt') or '').strip()
            lab = 'Screenshot' + (f': {alt}' if alt and len(alt) < 60 and not re.search(r'\.(png|jpe?g|gif)$', alt, re.I) else '')
            s.out.append(f'<a class="media img" href="{html.escape(s.url)}" target="_blank" rel="noopener" title="Screenshots open on the original article">{html.escape(lab)}</a>')
        elif t in ('iframe', 'video', 'source'):
            u = absu(a.get('src') or '')
            if not u: return
            m = re.search(r'youtube(?:-nocookie)?\.com/embed/([\w-]+)', u)
            if m: u, lab = f'https://www.youtube.com/watch?v={m.group(1)}', 'Watch video on YouTube'
            elif 'loom.com/embed/' in u: u, lab = u.replace('/embed/', '/share/'), 'Watch video on Loom'
            elif 'player.vimeo.com/video/' in u: u, lab = 'https://vimeo.com/' + re.search(r'video/(\d+)', u).group(1), 'Watch video on Vimeo'
            elif 'wistia' in u: lab = 'Watch video on Wistia'
            else: u, lab = s.url, 'Watch video on the original article'
            s.out.append(f'<a class="media vid" href="{html.escape(u)}" target="_blank" rel="noopener">{lab}</a>')

    def handle_endtag(s, t):
        if t in ('script', 'style', 'svg', 'button', 'nav'):
            s.skip = max(0, s.skip - 1); return
        if s.skip: return
        if t == 'h1': t = 'h2'
        want = t
        if t == 'a':
            for x in reversed(s.stack):
                if x in ('a', 'a~'): want = x; break
            else: return
        elif t not in KEEP or t in VOID or t not in s.stack:
            return
        while s.stack:
            x = s.stack.pop()
            if x != 'a~':
                s.out.append('</table></div>' if x == 'table' else f'</{x}>')
            if x == want: break

    def handle_data(s, data):
        if s.skip: return
        s.out.append(html.escape(data, quote=False))

    def result(s):
        while s.stack:
            x = s.stack.pop()
            if x != 'a~': s.out.append('</table></div>' if x == 'table' else f'</{x}>')
        h = ''.join(s.out)
        parts = re.split(r'(<pre>.*?</pre>)', h, flags=re.S)
        h = ''.join(x if x.startswith('<pre>') else re.sub(r'\s+', ' ', x) for x in parts)
        h = re.sub(r'\s*(</?(?:p|li|ul|ol|tr|td|th|tbody|thead|table|div|h[2-6])\b[^>]*>)\s*', r'\1', h)
        for _ in range(3):
            h = re.sub(r'<(p|li|strong|b|em|i|h[2-6])>(\s|<br>)*</\1>', '', h)
        h = re.sub(r'(<br>\s*){3,}', '<br><br>', h)
        h = re.sub(r'<p>(<br>)+', '<p>', h)
        return h.strip()


# ---- tree in the template's shape: {k, n, c, a, total}
placed = {}
def conv(n, top_name, chain):
    node = {"k": f"c{n['id']}", "n": n["n"], "c": [], "a": []}
    for a in n["a"]:
        if a["id"] in pages:
            node["a"].append(a["id"])
            placed.setdefault(a["id"], (top_name, chain))
    for c in n["c"]:
        child = conv(c, top_name, chain + [c["n"]])
        if child["total"]:
            node["c"].append(child)
    node["total"] = len(node["a"]) + sum(c["total"] for c in node["c"])
    return node

roots = [conv(n, n["n"], []) for n in tree]
for r in roots: r["d"] = next(n["d"] for n in tree if f"c{n['id']}" == r["k"])
roots = [r for r in roots if r["total"]]

idx, bodies = [], {}
for aid, r in pages.items():
    if aid not in placed: continue
    top, chain = placed[aid]
    sp = San(r["u"]); sp.feed(r["html"] or ""); body = sp.result()
    if r.get("desc") and r["desc"].strip() and r["desc"].strip() not in body:
        body = f'<p class="lede">{html.escape(r["desc"].strip(), quote=False)}</p>' + body
    idx.append({"id": aid, "t": r["t"], "cat": top, "path": chain, "ty": top, "u": r["u"], "up": r["up"]})
    bodies[aid] = body
idx.sort(key=lambda a: a["t"].lower())

meta = {
    "name": "Encompass", "source": BASE + "/en-us/", "sourceName": "Encompass help center",
    "scraped": "2026-11-14", "count": len(idx), "filterLabel": "Module",
    "types": [r["n"] for r in roots],
    "itCats": ["Platform", "DevOps", "Global Data"],
    "searches": ["handheld", "printer", "login", "password", "permissions", "sync", "install", "error", "Zebra", "QuickBooks", "import", "API"],
    "disclaimer": "Not affiliated with Encompass Technologies.",
}
json.dump({"meta": meta, "tree": roots, "idx": idx}, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
json.dump(bodies, open(os.path.join(OUT, "articles.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(idx), "articles;", [(r["n"], r["total"]) for r in roots])
print("unplaced pages:", len(set(pages) - set(placed)))
