// Static JSON "API" for agents (OpenResearch, Claude Code, Codex) and the chat Worker: public/neurips/api/.
// Rebuild after export.py: node scripts/neurips/build-api.mjs. check-neurips.mjs verifies it is in sync.
// Cloudflare's free plan allows 20,000 static files, so per-paper records are sharded (SHARD papers per file).
import { readFile, writeFile, mkdir, rm, readdir } from 'node:fs/promises';
const dir = 'public/neurips', m = JSON.parse(await readFile(`${dir}/data/map.json`, 'utf8'));
const A = []; for (const [part, from] of m.absParts) { const a = JSON.parse(await readFile(`${dir}/data/abstracts-${part}.json`, 'utf8')); a.forEach((t, k) => A[from + k] = t); }
const P = m.p, n = P.t.length, NN = m.nNeurips, KIND = ['poster', 'spotlight', 'oral'], base = 'https://vincentychu.com/neurips', SHARD = 20;
const ext = i => i >= NN;
const venue = i => ext(i) ? m.venues[P.vn[i]] || 'Elsewhere' : `NeurIPS ${P.yr[i]}`;
const paper = i => ({
  id: i, title: P.t[i], authors: P.a[i] ? P.a[i].split(', ') : [], year: P.yr[i], venue: venue(i), neurips: !ext(i),
  institutions: [...new Set(P.ai[i].filter(k => k >= 0))].map(k => m.inst[k]),
  kind: ext(i) ? null : KIND[P.k[i]], track: ext(i) ? null : P.tr[i] === 'D&B' ? 'Datasets & Benchmarks' : P.tr[i] || 'Main',
  citations: P.cc[i] || 0, landmark: !!P.lm[i], topic: P.f[i], area: P.c[i],
  arxiv: P.ax[i] || null, arxiv_category: P.ax[i] && P.ac[i] >= 0 ? m.cats[P.ac[i]] || null : null, arxiv_first_posted: P.ad[i] || null,
  alphaxiv: P.ax[i] ? `https://www.alphaxiv.org/abs/${P.ax[i]}` : null,
  openreview: P.u[i] ? `https://openreview.net/forum?id=${P.u[i]}` : null,
  url: ext(i) ? `https://www.semanticscholar.org/paper/${P.ex[i]}` : `https://neurips.cc/virtual/${P.yr[i]}/poster/${P.v[i]}`, map: `${base}/#p=${i}`,
  neighbors: P.nn[i], abstract: A[i] || null
});
await rm(`${dir}/api`, {recursive: true, force: true}); await mkdir(`${dir}/api/topic`, {recursive: true}); await mkdir(`${dir}/api/p`, {recursive: true});
const members = m.f.map(() => []); for (let i = 0; i < n; i++) members[P.f[i]].push(i);
const index = {
  about: `Every NeurIPS paper ${m.years[0]}-${m.years.at(-1)} (main, Datasets & Benchmarks, Position) plus landmark papers from other venues, embedded with bge-small-en-v1.5 and clustered into areas and topics. Citations from OpenAlex / Semantic Scholar. See SKILL.md.`,
  papers: n, neurips_papers: NN, landmark_papers_elsewhere: n - NN, years: m.years, source: `${base}/`, shard_size: SHARD,
  areas: m.c.map((c, i) => ({id: i, name: c.name, blurb: c.blurb, papers: c.n, per_year: Object.fromEntries(m.years.map((y, k) => [y, c.yrs[k]]))})),
  topics: m.f.map((f, i) => ({id: i, name: f.name, blurb: f.blurb, area: f.c, papers: members[i].length, per_year: Object.fromEntries(m.years.map((y, k) => [y, f.yrs[k]])), landmarks: f.lm, url: `${base}/api/topic/${i}.json`}))
};
await writeFile(`${dir}/api/index.json`, JSON.stringify(index, null, 1));
const score = i => (P.cc[i] || 0) / Math.max(1, 2027 - P.yr[i]) + P.k[i] * 3;
for (let f = 0; f < m.f.length; f++) {
  const ids = [...members[f]].sort((a, b) => P.lm[b] - P.lm[a] || score(b) - score(a));
  await writeFile(`${dir}/api/topic/${f}.json`, JSON.stringify({id: f, name: m.f[f].name, blurb: m.f[f].blurb, area: m.f[f].c, area_name: m.c[m.f[f].c].name,
    per_year: index.topics[f].per_year, landmarks: m.f[f].lm, papers: ids.map(paper)}));
}
const tsv = ['id\ttitle\tauthors\tyear\tvenue\tkind\ttrack\tcitations\tlandmark\ttopic\ttopic_name\tarxiv'];
for (let i = 0; i < n; i++) { const p = paper(i); tsv.push([i, p.title, p.authors.join(', '), p.year, p.venue, p.kind || '', p.track || '', p.citations, p.landmark ? 1 : 0, p.topic, m.f[p.topic].name, p.arxiv || ''].map(v => String(v).replace(/[\t\n]+/g, ' ')).join('\t')); }
await writeFile(`${dir}/api/papers.tsv`, tsv.join('\n') + '\n');
// Chat Worker records: api/p/<floor(id/SHARD)>.json = array of compact papers.
for (let s = 0; s * SHARD < n; s++) {
  const rows = [];
  for (let i = s * SHARD; i < Math.min(n, (s + 1) * SHARD); i++) { const au = P.a[i] ? P.a[i].split(', ') : [];
    rows.push({id: i, t: P.t[i], a: au.slice(0, 6).join(', ') + (au.length > 6 ? ` +${au.length - 6}` : ''), v: venue(i) + (ext(i) ? ' ' + P.yr[i] : ''), k: ext(i) ? '' : KIND[P.k[i]], c: P.cc[i] || 0, lm: P.lm[i], f: m.f[P.f[i]].name, ax: P.ax[i] || '', ab: A[i] || ''}); }
  await writeFile(`${dir}/api/p/${s}.json`, JSON.stringify(rows));
}
// Two-stage retrieval for the chat Worker (keeps it inside the free plan's CPU budget): topic centroids, then members.
const E = new Int8Array((await readFile(`${dir}/data/emb.i8`)).buffer.slice(0)), D = 384, C = new Int8Array(m.f.length * D);
for (let f = 0; f < m.f.length; f++) {
  const c = new Float64Array(D); for (const i of members[f]) for (let k = 0; k < D; k++) c[k] += E[i * D + k];
  const nrm = Math.hypot(...c) || 1; for (let k = 0; k < D; k++) C[f * D + k] = Math.max(-127, Math.min(127, Math.round(c[k] / nrm * 127)));
}
await writeFile(`${dir}/api/centroids.i8`, C);
await writeFile(`${dir}/api/members.json`, JSON.stringify(members));
console.log(`api: ${m.f.length} topics, ${Math.ceil(n / SHARD)} paper shards, ${n} papers`);
