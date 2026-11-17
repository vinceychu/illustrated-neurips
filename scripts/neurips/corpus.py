"""Merge neurips.cc accepted-paper dumps for several years into one corpus.
Usage: corpus.py raw_dir out.json [arxiv.json]
raw_dir/<year>.json = https://neurips.cc/static/virtual/data/neurips-<year>-orals-posters.json
arxiv.json (arxiv_match.py output) fills abstracts that neurips.cc doesn't publish yet (2026: OpenReview
keeps camera-ready papers private until the conference)."""
import json, ast, sys, os, re, html
raw_dir, out = sys.argv[1], sys.argv[2]
AX = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and os.path.exists(sys.argv[3]) else {}
years = sorted(int(f[:4]) for f in os.listdir(raw_dir) if re.fullmatch(r'\d{4}\.json', f))
P = []
def authors(i):
    raw = i['authors'] if isinstance(i['authors'], list) else ast.literal_eval(i['authors'] or '[]')
    return [[a.get('fullname', '').strip(), (a.get('institution') or '').strip()] for a in raw if a.get('fullname')]
for y in years:
    R = json.load(open(f'{raw_dir}/{y}.json'))['results']
    orals = {i['name'].strip() for i in R if i['eventtype'] == 'Oral'}
    spots = {i['name'].strip() for i in R if i['eventtype'] == 'Spotlight'}
    seen = set()
    for i in R:
        if i['eventtype'] != 'Poster': continue
        t = ' '.join(html.unescape(i['name'] or '').split())
        if not t or t in seen: continue
        seen.add(t)
        dec = (i.get('decision') or '').lower()
        k = 'oral' if t in orals or 'oral' in dec else 'spotlight' if t in spots or 'spotlight' in dec else 'poster'
        src = (i.get('sourceurl') or '')
        tr = 'D&B' if re.search(r'Datasets|Evaluations', src) else 'Position' if 'Position' in src else \
             'Journal' if re.search(r'journal|TMLR|jmlr|rescience', src, re.I) else 'Main'
        pu = str(i.get('paper_url') or '').replace('None', '') or str(i.get('paper_pdf_url') or '').replace('None', '')
        m = re.search(r'openreview\.net/forum\?id=([\w-]+)', pu)
        ab = ' '.join((i.get('abstract') or '').split())
        ax = AX.get(f'{y}|{t}') or {}
        P.append(dict(t=t, y=y, au=authors(i), ab=ab or ax.get('ab', ''), abs='neurips' if ab else 'arxiv' if ax.get('ab') else '',
                      k=k, tr=tr, tp=(i.get('topic') or '').replace('None', ''), u=m.group(1) if m else '',
                      pu=pu if pu.startswith('http') and not m else '', v=int(i['id'])))
json.dump(P, open(out, 'w'), ensure_ascii=False)
from collections import Counter
print(len(P), dict(Counter(p['y'] for p in P)), 'no abstract:', dict(Counter(p['y'] for p in P if not p['ab'])))
