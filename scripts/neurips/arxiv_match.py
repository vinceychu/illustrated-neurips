"""Match paper titles to arXiv (id, primary category, first-posted date, abstract).
Usage: arxiv_match.py corpus.json out.json   (resumable; arXiv asks for <=1 request / 3 s)
corpus.json: list of {t, y}. A hit must be first posted between Jan of year-2 and Dec of year+1,
otherwise it's a title collision with an older/newer paper."""
import json, re, sys, time, urllib.request, urllib.parse, difflib, xml.etree.ElementTree as ET
src, out = sys.argv[1], sys.argv[2]
P = json.load(open(src))
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
try: res = json.load(open(out))
except Exception: res = {}
key = lambda p: f"{p['y']}|{p['t']}"
todo = [p for p in P if key(p) not in res]
ns = {'a': 'http://www.w3.org/2005/Atom', 'x': 'http://arxiv.org/schemas/atom'}
B = 100  # POSTed, so the query can be long
for k in range(0, len(todo), B):
    batch = todo[k:k+B]
    q = ' OR '.join('ti:"%s"' % ' '.join(re.sub(r'[^\w\s-]', ' ', p['t']).replace('-', ' ').split()[:14]) for p in batch)
    body = urllib.parse.urlencode({'search_query': q, 'max_results': B * 5}).encode()
    x = None
    for attempt in range(5):
        try:
            x = urllib.request.urlopen(urllib.request.Request('https://export.arxiv.org/api/query', data=body, headers={'User-Agent': 'paper-map/1.0', 'Content-Type': 'application/x-www-form-urlencoded'}), timeout=120).read(); break
        except Exception:
            time.sleep(10 * (attempt + 1))
    if x is None: continue
    ents = []
    for e in ET.fromstring(x).findall('a:entry', ns):
        t = ' '.join(e.find('a:title', ns).text.split())
        aid = e.find('a:id', ns).text.rsplit('/abs/', 1)[-1]
        pc = e.find('x:primary_category', ns)
        ents.append((norm(t), dict(id=re.sub(r'v\d+$', '', aid), cat=pc.get('term') if pc is not None else '',
            date=e.find('a:published', ns).text[:10], ab=' '.join((e.find('a:summary', ns).text or '').split()))))
    for p in batch:
        n = norm(p['t']); lo, hi = f"{p['y'] - 2}-01", f"{p['y'] + 1}-12-99"
        ok = [(m, v) for m, v in ents if lo <= v['date'] <= hi]
        hit = next((v for m, v in ok if m == n), None)
        if not hit:
            best = max(ok, key=lambda mv: difflib.SequenceMatcher(None, mv[0], n).ratio(), default=None)
            if best and difflib.SequenceMatcher(None, best[0], n).ratio() > 0.92: hit = best[1]
        res[key(p)] = hit or {}
    json.dump(res, open(out, 'w'))
    print(k + len(batch), len(todo), sum(1 for v in res.values() if v), flush=True)
    time.sleep(3.1)
