// Content-hash cache busting for /neurips/ (public/_headers serves these as immutable for a year).
// node scripts/neurips/stamp.mjs        → rewrite ?v= stamps   |   --check → fail if any stamp is stale
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const dir = 'public/neurips', check = process.argv.includes('--check');
const h8 = async f => createHash('sha256').update(await readFile(`${dir}/${f}`)).digest('hex').slice(0, 8);
let stale = [];
async function stamp(file, targets) {
  let s = await readFile(`${dir}/${file}`, 'utf8'), o = s;
  for (const t of targets) { const v = await h8(t), re = new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\?v=[0-9a-z]+', 'g'); if (!re.test(s)) throw Error(`${file}: no ${t}?v= stamp`); s = s.replace(re, `${t}?v=${v}`); }
  if (s !== o) { stale.push(file); if (!check) await writeFile(`${dir}/${file}`, s); }
}
await stamp('neurips.js', ['data/map.json', 'data/emb.i8']);
// Abstracts are split per year (data/abstracts-<year>.json); one stamp (ABSV) covers them all.
{ const parts = (await readdir(`${dir}/data`)).filter(f => /^abstracts-.+\.json$/.test(f)).sort(), hh = createHash('sha256');
  for (const f of parts) hh.update(await readFile(`${dir}/data/${f}`));
  const v = hh.digest('hex').slice(0, 8), f = `${dir}/neurips.js`, s = await readFile(f, 'utf8'), o = s.replace(/ABSV = '[0-9a-z]+'/, `ABSV = '${v}'`);
  if (!/ABSV = '/.test(s)) throw Error('neurips.js: no ABSV stamp');
  if (o !== s) { stale.push('neurips.js (abstracts)'); if (!check) await writeFile(f, o); } }
await stamp('index.html', ['neurips.js', 'neurips.css']);
if (check && stale.length) throw Error(`neurips: stale ?v= stamps in ${stale.join(', ')}; run node scripts/neurips/stamp.mjs`);
console.log(check ? 'neurips: cache stamps ok' : `neurips: stamped ${stale.join(', ') || 'nothing (up to date)'}`);
