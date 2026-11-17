"""Build public/neurips/data/ from layout + names + arXiv matches + citations + landmarks.
Usage: export.py prefix emb.npy names.json arxiv.json cites.json landmarks.json outdir
Writes map.json (columns), abstracts-<part>.json (one per year + 'ext'), emb.i8 (int8, NeurIPS papers then landmarks)."""
import json, sys, re, html, collections, numpy as np
pre, embf, names, arx, cites, lmf, outdir = sys.argv[1:8]
P = json.load(open(pre + '_laid.json')); C = json.load(open(pre + '_clusters.json')); NM = json.load(open(names))
AX = json.load(open(arx)); CI = json.load(open(cites)); LM = json.load(open(lmf))
NP = len(P)
ALIAS = {'mit': 'Massachusetts Institute of Technology', 'uc berkeley': 'University of California, Berkeley', 'berkeley': 'University of California, Berkeley',
  'shanghai jiaotong university': 'Shanghai Jiao Tong University', 'cmu': 'Carnegie Mellon University', 'ucla': 'University of California, Los Angeles',
  'uiuc': 'University of Illinois at Urbana-Champaign', 'university of illinois urbana-champaign': 'University of Illinois at Urbana-Champaign',
  'university of illinois, urbana champaign': 'University of Illinois at Urbana-Champaign',
  'bytedance inc.': 'ByteDance', 'bytedance seed': 'ByteDance', 'bytedance': 'ByteDance', 'huawei technologies ltd.': 'Huawei', 'huawei': 'Huawei', 'huawei noah\'s ark lab': 'Huawei',
  'meta ai': 'Meta', 'meta fair': 'Meta', 'fair, meta': 'Meta', 'meta': 'Meta', 'facebook': 'Meta', 'facebook ai research': 'Meta', 'facebook ai': 'Meta', 'meta (united states)': 'Meta',
  'microsoft research': 'Microsoft', 'microsoft': 'Microsoft', 'microsoft (united states)': 'Microsoft', 'microsoft research asia': 'Microsoft',
  'google research': 'Google', 'google': 'Google', 'google (united states)': 'Google', 'google brain': 'Google',
  'deepmind': 'Google DeepMind', 'google deepmind': 'Google DeepMind', 'alibaba group': 'Alibaba', 'alibaba': 'Alibaba', 'tencent': 'Tencent', 'tencent ai lab': 'Tencent',
  'hong kong university of science and technology': 'Hong Kong University of Science and Technology', 'hkust': 'Hong Kong University of Science and Technology',
  'chinese university of hong kong': 'The Chinese University of Hong Kong', 'cuhk': 'The Chinese University of Hong Kong', 'university of hong kong': 'The University of Hong Kong',
  'sun yat-sen university': 'Sun Yat-sen University', 'eth zurich': 'ETH Zurich', 'eth zürich': 'ETH Zurich', 'epfl': 'EPFL', 'kaist': 'KAIST',
  'ustc': 'University of Science and Technology of China', 'nus': 'National University of Singapore', 'ntu': 'Nanyang Technological University',
  'nvidia': 'NVIDIA', 'nvidia (united states)': 'NVIDIA', 'amazon': 'Amazon', 'apple': 'Apple', 'openai': 'OpenAI', 'openai (united states)': 'OpenAI', 'anthropic': 'Anthropic',
  'stanford university': 'Stanford University', 'stanford': 'Stanford University', 'tsinghua university': 'Tsinghua University', 'peking university': 'Peking University'}
def canon(s):
    s = ' '.join(html.unescape(s or '').split()).strip(' ,;')
    parts = [p.strip() for p in s.split(',')]
    if len(parts) == 2 and parts[0].lower() == parts[1].lower(): s = parts[0]
    k = s.lower(); k2 = re.sub(r'^the ', '', k)
    return ALIAS.get(k) or ALIAS.get(k2) or s
VSHORT = {'trans. mach. learn. res.': 'TMLR', 'j. mach. learn. res.': 'JMLR', 'ieee trans. pattern anal. mach. intell.': 'TPAMI',
  'arxiv.org': 'arXiv', 'expert systems with applications': 'Expert Syst. Appl.', 'ieee transactions on neural networks and learning systems': 'IEEE TNNLS',
  'nature machine intelligence': 'Nature Mach. Intell.', 'proceedings of the national academy of sciences of the united states of america': 'PNAS'}
for p in LM: p['venue'] = VSHORT.get((p['venue'] or '').lower(), p['venue']) or 'arXiv'
ALL = [dict(p, ext=0) for p in P] + [dict(p, ext=1, k='poster', tr='Ext', u='', pu='', v=0) for p in LM]
spell = collections.defaultdict(collections.Counter)
for p in ALL:
    for _, ins in p['au']:
        c = canon(ins)
        if c: spell[c.lower()][c] += 1
disp = {k: v.most_common(1)[0][0] for k, v in spell.items()}
cnt = collections.Counter(disp[canon(ins).lower()] for p in ALL for _, ins in p['au'] if canon(ins))
inst = [k for k, v in cnt.most_common() if v >= 2]; ii = {k: i for i, k in enumerate(inst)}
key = lambda p: f"{p['y']}|{p['t']}"
def axof(p):
    if p['ext']: return {'id': p['ax']} if p['ax'] else {}
    return AX.get(key(p)) or {}
cats = collections.Counter(axof(p).get('cat') for p in ALL if axof(p).get('cat'))
catl = [c for c, _ in cats.most_common()]; ci = {c: i for i, c in enumerate(catl)}
venues = [v for v, _ in collections.Counter(p['venue'] or 'Other' for p in LM).most_common()]; vi = {v: i for i, v in enumerate(venues)}
cc = [p['cc'] if p['ext'] else (CI.get(key(p)) or {}).get('c', 0) for p in ALL]
years = sorted({p['y'] for p in ALL if not p['ext']})
# Landmarks: per topic, the most-cited papers per year since publication (NeurIPS or not), at least 25 citations.
lm = [0] * len(ALL); topic_lm = collections.defaultdict(list)
for f in range(len(C['fine'])):
    idx = [i for i, p in enumerate(ALL) if p['f'] == f and cc[i] >= 25]
    idx.sort(key=lambda i: -cc[i] / max(1, 2027 - ALL[i]['y']))
    for i in idx[:10]: lm[i] = 1; topic_lm[f].append(i)
def nm(level, c):
    d = NM[level].get(str(c['id'])) or {}; b = d.get('blurb') or ''
    return d.get('name') or ', '.join(t.title() for t in c['terms'][:3]), b if len(b) >= 20 else 'Keywords: ' + ', '.join(c['terms'][:6])
out = {'years': years, 'c': [], 'f': [], 'inst': inst, 'cats': catl, 'venues': venues, 'nNeurips': NP,
       'p': {k: [] for k in 't a ai x y c f k tr u v ax ac ad nn yr cc lm vn ex'.split()}}
for c in C['coarse']:
    n, b = nm('coarse', c); out['c'].append(dict(name=n, blurb=b, n=c['n'], x=round(c['xy'][0] * 10000), y=round(c['xy'][1] * 10000), yrs=[c['years'].get(str(y), c['years'].get(y, 0)) for y in years]))
used = collections.Counter()
for c in C['fine']:
    n, b = nm('fine', c); used[n] += 1
    if used[n] > 1: n = f"{n} ({out['c'][c['parent']]['name']})" if used[n] == 2 else f"{n} {used[n]}"
    out['f'].append(dict(name=n, blurb=b, n=c['n'], c=c['parent'], x=round(c['xy'][0] * 10000), y=round(c['xy'][1] * 10000),
        yrs=[c['years'].get(str(y), c['years'].get(y, 0)) for y in years], lm=topic_lm[c['id']]))
K = {'poster': 0, 'spotlight': 1, 'oral': 2}
for i, p in enumerate(ALL):
    q = out['p']; a = axof(p)
    q['t'].append(p['t']); q['a'].append(', '.join(n for n, _ in p['au']))
    q['ai'].append([ii.get(disp.get(canon(ins).lower(), ''), -1) if canon(ins) else -1 for _, ins in p['au']])
    q['x'].append(round(p['x'] * 10000)); q['y'].append(round(p['y2'] * 10000)); q['c'].append(p['c']); q['f'].append(p['f'])
    q['k'].append(K[p['k']]); q['tr'].append('' if p['tr'] == 'Main' else p['tr']); q['u'].append(p['u']); q['v'].append(p['v'])
    q['ax'].append(a.get('id', '')); q['ac'].append(ci.get(a.get('cat'), -1)); q['ad'].append(a.get('date', '')[:7]); q['nn'].append(p['nn'])
    q['yr'].append(p['y']); q['cc'].append(cc[i]); q['lm'].append(lm[i]); q['vn'].append(vi[p['venue'] or 'Other'] if p['ext'] else -1)
    q['ex'].append(p['oa'] if p['ext'] else (p.get('pu') or ''))
E = np.vstack([np.load(embf), np.array([p['emb'] for p in LM], dtype=np.float32).reshape(-1, 384)]); SCALE = 300.0
out['embScale'] = SCALE
np.clip(np.round(E * SCALE), -127, 127).astype(np.int8).tofile(outdir + '/emb.i8')
parts = []
for y in years + ['ext']:
    idx = [i for i, p in enumerate(ALL) if (p['ext'] if y == 'ext' else (not p['ext'] and p['y'] == y))]
    if not idx: continue
    assert idx == list(range(idx[0], idx[-1] + 1)), 'abstract parts must be contiguous'
    json.dump([ALL[i]['ab'] for i in idx], open(f'{outdir}/abstracts-{y}.json', 'w'), separators=(',', ':'), ensure_ascii=False)
    parts.append([str(y), idx[0], idx[-1] + 1])
out['absParts'] = parts
json.dump(out, open(outdir + '/map.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('papers', len(ALL), 'neurips', NP, 'landmarks(ext)', len(LM), 'flagged', sum(lm), 'inst', len(inst), 'on arXiv', sum(1 for x in out['p']['ax'] if x),
      'with cites', sum(1 for x in cc if x), 'years', years)
