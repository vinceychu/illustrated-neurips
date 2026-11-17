"""Citation counts for the corpus. Usage: citations.py corpus.json arxiv.json out.json
1. OpenAlex works whose primary source is NeurIPS (S4363606243), matched by normalized title + year.
2. Papers with an arXiv id: Semantic Scholar batch (500 ids/request), which also counts arXiv-version citations.
Result: {"<year>|<title>": {"oa": n, "s2": n, "c": max}}. Resumable."""
import json, re, sys, time, urllib.request, urllib.parse
corpus, arxiv, out = sys.argv[1:4]
P = json.load(open(corpus)); AX = json.load(open(arxiv))
try: R = json.load(open(out))
except Exception: R = {}
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
key = lambda p: f"{p['y']}|{p['t']}"
UA = {'User-Agent': 'paper-map/1.0'}
def get(url, data=None, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={**UA, **({'Content-Type': 'application/json'} if data else {})})
            return json.load(urllib.request.urlopen(req, timeout=90))
        except Exception as e:
            time.sleep(min(90, 5 * 2 ** i))
    return None
save = lambda: json.dump(R, open(out, 'w'))
by = {}
for p in P: by.setdefault((p['y'], norm(p['t'])), p)

# Keyless OpenAlex: page (not cursor) paging, ~1,000 requests/day shared per IP, so no per-title searches.
if not R.get('_oa_done'):
    for y in range(min(p['y'] for p in P), max(p['y'] for p in P) + 1):
        for page in range(1, 51):
            j = get(f'https://api.openalex.org/works?filter=primary_location.source.id:S4363606243,publication_year:{y}&per_page=200&page={page}&select=title,cited_by_count,publication_year')
            if not j or not j['results']: break
            for w in j['results']:
                for yy in (y, y - 1, y + 1):
                    p = by.get((yy, norm(w['title'])))
                    if p: R.setdefault(key(p), {})['oa'] = max(R.get(key(p), {}).get('oa', 0), w['cited_by_count']); break
            time.sleep(0.2)
        print('openalex source', y, sum(1 for k, v in R.items() if k.startswith(f'{y}|') and 'oa' in v), flush=True)
    R['_oa_done'] = 1; save()

ids = [(key(p), AX[key(p)]['id']) for p in P if (AX.get(key(p)) or {}).get('id') and 's2' not in R.get(key(p), {})]
for k in range(0, len(ids), 500):
    b = ids[k:k + 500]
    j = get('https://api.semanticscholar.org/graph/v1/paper/batch?fields=citationCount', data=json.dumps({'ids': ['ARXIV:' + a for _, a in b]}).encode(), tries=12)
    if j is None: print('s2 batch failed', k, flush=True); continue
    for (kk, _), r in zip(b, j): R.setdefault(kk, {})['s2'] = (r or {}).get('citationCount') or 0
    save(); print('s2', k + len(b), len(ids), flush=True); time.sleep(1.5)
for k, v in R.items():
    if isinstance(v, dict): v['c'] = max(v.get('oa', 0) if 'oa' in v else 0, v.get('s2', 0))
save()
print('with citations', sum(1 for v in R.values() if isinstance(v, dict) and v.get('c')))
