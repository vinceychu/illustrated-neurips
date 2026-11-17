"""Name clusters. Usage: name.py slim.json names.json
Runs Claude Code headless (`claude -p`) on batches of clusters and asks for strict JSON.
Falls back to keywords for anything it doesn't return (export.py does that)."""
import json, sys, subprocess, re, os, concurrent.futures as cf
d = json.load(open(sys.argv[1])); out_f = sys.argv[2]
try: out = json.load(open(out_f))
except Exception: out = {'coarse': {}, 'fine': {}}
CLAUDE = os.environ.get('CLAUDE', 'claude')
RULE = ('You name topic clusters on an interactive map of every NeurIPS paper from 2020 to 2026. For each cluster you get '
        'distinctive keywords, representative titles (year in brackets) and paper counts per year. Return ONLY a JSON object '
        'mapping cluster id to {"name": precise %s topic name in Title Case, no generic words like Advances/Methods/Approaches, '
        'names must be distinct from each other; "blurb": ONE plain sentence of 14-26 words saying what these papers do (concrete '
        'problems and techniques) and, if the yearly counts show it, how the field moved (e.g. "growing fast since 2023")}.')
def run(level, batch, words):
    ctx = '\n\n'.join(f"## {c['id']}\nKeywords: {', '.join(c['terms'])}\nPapers per year: {c['years']}\nTitles:\n- " + '\n- '.join(c['titles'][:10]) for c in batch)
    for _ in range(3):
        r = subprocess.run([CLAUDE, '-p', RULE % words + '\n\n' + ctx, '--output-format', 'text', '--max-turns', '1'], capture_output=True, text=True, timeout=900)
        m = re.search(r'\{.*\}', r.stdout, re.S)
        try:
            j = json.loads(m.group(0)); return level, {str(k): v for k, v in j.items()}
        except Exception: continue
    return level, {}
jobs = [('coarse', d['coarse'], '2-4 word')]
fine = [c for c in d['fine'] if str(c['id']) not in out['fine']]
jobs += [('fine', fine[k:k + 30], '2-5 word') for k in range(0, len(fine), 30)]
if str(d['coarse'][0]['id']) in out['coarse']: jobs = jobs[1:]
with cf.ThreadPoolExecutor(4) as ex:
    for level, res in ex.map(lambda j: run(*j), jobs):
        out[level].update(res); json.dump(out, open(out_f, 'w'), indent=0, ensure_ascii=False)
        print(level, len(out[level]), flush=True)
print('coarse', len(out['coarse']), '/', len(d['coarse']), 'fine', len(out['fine']), '/', len(d['fine']))
