import { readFile, stat, readdir } from 'node:fs/promises';
const m = JSON.parse(await readFile('public/neurips/data/map.json', 'utf8'));
const n = m.p.t.length, NN = m.nNeurips;
if (NN < 25000) throw Error(`neurips: only ${NN} NeurIPS papers`);
if (!(m.years?.[0] <= 2020 && m.years.at(-1) >= 2026)) throw Error('neurips: years should span 2020-2026');
for (const k of ['a', 'ai', 'x', 'y', 'c', 'f', 'k', 'tr', 'u', 'v', 'ax', 'ac', 'ad', 'nn', 'yr', 'cc', 'lm', 'vn', 'ex']) if (m.p[k]?.length !== n) throw Error(`neurips: column ${k} length mismatch`);
let absN = 0, last = 0;
for (const [part, from, to] of m.absParts) {
  if (from !== last) throw Error('neurips: abstract parts not contiguous'); last = to;
  const a = JSON.parse(await readFile(`public/neurips/data/abstracts-${part}.json`, 'utf8'));
  if (a.length !== to - from) throw Error(`neurips: abstracts-${part} length mismatch`); absN += a.filter(Boolean).length;
  if ((await stat(`public/neurips/data/abstracts-${part}.json`)).size > 24e6) throw Error(`neurips: abstracts-${part} exceeds the 25 MiB asset limit`);
}
if (last !== n) throw Error('neurips: abstract parts do not cover every paper');
if ((await readdir('public/neurips/data')).includes('abstracts.json')) throw Error('neurips: stale data/abstracts.json');
if (m.p.c.some(c => !m.c[c]) || m.p.f.some(f => !m.f[f])) throw Error('neurips: dangling cluster id');
if (m.c.some(c => !c.name) || m.f.some(f => !f.name)) throw Error('neurips: unnamed cluster');
if (new Set(m.f.map(f => f.name)).size !== m.f.length) throw Error('neurips: duplicate topic names');
if (m.p.ai.some(l => l.some(k => k >= m.inst.length))) throw Error('neurips: dangling institution id');
if (m.p.nn.some(l => l.length !== 10 || l.some(j => j < 0 || j >= n))) throw Error('neurips: bad neighbour list');
if (m.p.yr.some((y, i) => i < NN && !m.years.includes(y))) throw Error('neurips: paper year outside years');
if (m.p.vn.some((v, i) => (i >= NN) !== (v >= 0))) throw Error('neurips: venue column must mark exactly the non-NeurIPS papers');
if (m.f.some(f => f.lm.some(i => !m.p.lm[i] || m.p.f[i] !== m.f.indexOf(f)))) throw Error('neurips: topic landmark list out of sync');
const onAx = m.p.ax.filter(Boolean).length;
if (onAx < n * 0.5) throw Error(`neurips: only ${onAx} arXiv links`);
if (m.p.ax.some(x => x && !/^\d{4}\.\d{4,5}$|^[a-z-]+(\.[A-Z]{2})?\/\d{7}$/.test(x))) throw Error('neurips: malformed arXiv id');
const dim = 384, e = await stat('public/neurips/data/emb.i8');
if (e.size !== n * dim) throw Error(`neurips: emb.i8 is ${e.size} bytes, expected ${n * dim}`);
if (!(m.embScale > 0)) throw Error('neurips: missing embScale');
console.log(`neurips: ${NN} NeurIPS papers ${m.years[0]}-${m.years.at(-1)} + ${n - NN} landmarks elsewhere, ${onAx} on arXiv, ${absN} abstracts, ${m.c.length} areas, ${m.f.length} topics, ${m.p.lm.filter(Boolean).length} landmarks`);
// Agent API (scripts/neurips/build-api.mjs) must match map.json.
const idx = JSON.parse(await readFile('public/neurips/api/index.json', 'utf8'));
if (idx.papers !== n || idx.topics.length !== m.f.length) throw Error('neurips: api/ is stale, run node scripts/neurips/build-api.mjs');
let apiN = 0; for (const t of idx.topics) { const j = JSON.parse(await readFile(`public/neurips/api/topic/${t.id}.json`, 'utf8')); if (j.papers.length !== t.papers) throw Error(`neurips: api topic ${t.id} count mismatch`); apiN += j.papers.length; }
if (apiN !== n) throw Error('neurips: api topics do not cover every paper');
const tsvN = (await readFile('public/neurips/api/papers.tsv', 'utf8')).trim().split('\n').length - 1;
if (tsvN !== n) throw Error('neurips: api/papers.tsv is stale');
const shards = (await readdir('public/neurips/api/p')).length;
if (shards !== Math.ceil(n / idx.shard_size)) throw Error('neurips: api/p shards stale');
const mem = JSON.parse(await readFile('public/neurips/api/members.json', 'utf8'));
if (mem.flat().length !== n || (await stat('public/neurips/api/centroids.i8')).size !== m.f.length * dim) throw Error('neurips: chat retrieval index stale');
if (!/^---\nname: neurips-map\n/.test(await readFile('public/neurips/SKILL.md', 'utf8'))) throw Error('neurips: SKILL.md frontmatter');
let files = 0; const walk = async d => { for (const f of await readdir(d, {withFileTypes: true})) f.isDirectory() ? await walk(`${d}/${f.name}`) : files++; }; await walk('public');
if (files > 19000) throw Error(`public/ has ${files} files; Cloudflare's free plan allows 20,000`);
console.log(`neurips api: ${idx.topics.length} topic files, ${shards} shards, ${tsvN} rows; public/ ${files} files`);
