"""Landmark papers from outside NeurIPS for every topic (micro-field), 2020-2026.
Usage: landmarks.py prefix corpus_emb.npy out.json
For each fine cluster: Semantic Scholar papers matching its distinctive terms, sorted by citations, 2020-2026.
A candidate is kept only if bge-small puts it inside this topic (its nearest topic centroid is this one and it is
as close to the centroid as a typical member). Kept papers are embedded and placed with the fitted UMAP."""
import json, sys, re, time, pickle, urllib.request, urllib.parse, numpy as np
from sentence_transformers import SentenceTransformer
pre, embf, out = sys.argv[1:4]
P = json.load(open(pre + '_laid.json')); C = json.load(open(pre + '_clusters.json')); M = pickle.load(open(pre + '_umap.pkl', 'rb'))
E = np.load(embf); fine = np.array([p['f'] for p in P]); NF = len(C['fine'])
cent = np.array([E[fine == c].mean(0) for c in range(NF)]); cent /= np.linalg.norm(cent, axis=1, keepdims=True)
# typical member similarity per topic (25th percentile) = admission bar
bar = np.array([np.percentile(E[fine == c] @ cent[c], 25) for c in range(NF)])
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
have = {norm(p['t']) for p in P}
UA = {'User-Agent': 'paper-map/1.0'}
def get(url, tries=12):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90))
        except Exception: time.sleep(min(60, 2 * 2 ** i))
    return None
SHORT = [('learning representations', 'ICLR'), ('international conference on machine learning', 'ICML'), ('computer vision and pattern recognition', 'CVPR'),
  ('ieee international conference on computer vision', 'ICCV'), ('international conference on computer vision', 'ICCV'), ('european conference on computer vision', 'ECCV'),
  ('association for computational linguistics', 'ACL'), ('empirical methods in natural language', 'EMNLP'), ('north american chapter', 'NAACL'),
  ('aaai', 'AAAI'), ('international joint conference on artificial intelligence', 'IJCAI'), ('knowledge discovery and data mining', 'KDD'),
  ('transactions on machine learning research', 'TMLR'), ('journal of machine learning research', 'JMLR'), ('pattern analysis and machine intelligence', 'TPAMI'),
  ('robotics: science and systems', 'RSS'), ('conference on robot learning', 'CoRL'), ('arxiv', 'arXiv'), ('conference on learning theory', 'COLT'),
  ('artificial intelligence and statistics', 'AISTATS'), ('uncertainty in artificial intelligence', 'UAI'), ('web conference', 'WWW'), ('sigir', 'SIGIR')]
def short(v):
    l = (v or '').lower()
    return next((s for k, s in SHORT if k in l), v or 'arXiv')
# Candidates: Semantic Scholar bulk search on the topic's distinctive terms, sorted by citations, 2020-2026.
# (OpenAlex search needs an API key past ~100 searches/day.) Cached per topic so a rerun resumes.
CF = out + '.cache.json'
try: cache = json.load(open(CF))
except Exception: cache = {}
for c in C['fine']:
    if str(c['id']) not in cache:
        ts = [t for t in c['terms'] if len(t) > 3][:5]
        q = '|'.join(f'"{t}"' for t in ts)
        j = get('https://api.semanticscholar.org/graph/v1/paper/search/bulk?' + urllib.parse.urlencode({'query': q, 'sort': 'citationCount:desc', 'year': '2020-2026',
                'minCitationCount': 40, 'fields': 'title,year,citationCount,venue,externalIds,abstract,authors'}))
        if j is None: print('topic', c['id'], 'failed', flush=True); continue
        cache[str(c['id'])] = [d for d in j.get('data', [])[:80] if d.get('abstract') and d.get('title')]
        json.dump(cache, open(CF, 'w')); time.sleep(1.2)
    print('topic', c['id'], len(cache[str(c['id'])]), flush=True)
cand = {}
for cid, rows in cache.items():
    for d in rows:
        if norm(d['title']) in have or 'neural information processing' in (d.get('venue') or '').lower(): continue
        w = cand.setdefault(d['paperId'], {'id': d['paperId'], 'title': d['title'], 'publication_year': d['year'], 'cited_by_count': d['citationCount'],
            'venue': short(d.get('venue')), 'ab': d['abstract'], 'ax': (d.get('externalIds') or {}).get('ArXiv') or '', 'doi': (d.get('externalIds') or {}).get('DOI') or '',
            'au': [[a.get('name', ''), ''] for a in (d.get('authors') or [])[:40]], 'want': set()})
        w['want'].add(int(cid))
W = list(cand.values()); print('candidates', len(W), flush=True)
m = SentenceTransformer('BAAI/bge-small-en-v1.5')
X = m.encode([' '.join(w['title'].split()) + '. ' + w['ab'] for w in W], batch_size=64, show_progress_bar=False, normalize_embeddings=True)
S = X @ cent.T; best = S.argmax(1)
keep = [k for k in range(len(W)) if best[k] in W[k]['want'] and S[k, best[k]] >= bar[best[k]]]
by = {}
for k in keep: by.setdefault(int(best[k]), []).append(k)
final = []
for c, ks in by.items():
    ks.sort(key=lambda k: -W[k]['cited_by_count'] / max(1, 2027 - W[k]['publication_year']))
    final += ks[:8]
X = X[final]; U2 = M['u2'].transform(X); U2 = (U2 - M['lo']) / M['span'] + M['off']; U10 = M['u10'].transform(X)
res = []
for n, k in enumerate(final):
    w = W[k]; nnb = np.argsort(-(E @ X[n]))[:10].tolist()
    res.append(dict(t=' '.join(w['title'].split()), y=w['publication_year'], ab=w['ab'], cc=w['cited_by_count'], venue=w['venue'], au=w['au'],
        oa=w['id'], doi=w['doi'], ax=w['ax'], f=int(best[k]), c=int(M['coarse_of'][best[k]]),
        x=round(float(U2[n, 0]), 4), y2=round(float(U2[n, 1]), 4), nn=nnb, emb=X[n].tolist()))
json.dump(res, open(out, 'w'), ensure_ascii=False)
print('kept', len(res), 'topics with landmarks', len(by), 'of', NF)
