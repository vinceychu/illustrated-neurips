#!/usr/bin/env bash
# Final assembly of the map's site data:
#   citations top-up -> export -> agent API -> stamps -> checks.
#
# Usage: NEURIPS_DATA=/path/to/work/dir scripts/neurips/build_site_data.sh
# NEURIPS_DATA holds the pipeline's intermediate files (corpus.json, arxiv.json, emb.npy,
# names.json, landmarks.json, ...) and optionally a Python venv in $NEURIPS_DATA/venv.
# SITE_DIR is the website checkout that serves public/neurips/ (default: this repository).
set -euo pipefail
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
WORK=${NEURIPS_DATA:?set NEURIPS_DATA to the pipeline work directory}
S=$REPO/scripts/neurips
PY=${PYTHON:-$([ -x "$WORK/venv/bin/python" ] && echo "$WORK/venv/bin/python" || echo python3)}
SITE=${SITE_DIR:-$REPO}
D=$SITE/public/neurips/data

cd "$WORK"
python3 "$S/corpus.py" raw corpus_final.json arxiv.json   # same order as corpus.json; only abstracts may differ
python3 - <<'PYEOF'
import json
a = json.load(open('corpus.json')); b = json.load(open('corpus_final.json'))
assert [(p['y'], p['t']) for p in a] == [(p['y'], p['t']) for p in b], 'corpus order changed'
PYEOF
python3 "$S/citations.py" corpus.json arxiv.json cites.json > cites2.log 2>&1 || true
tail -1 cites2.log
rm -f "$D"/abstracts.json "$D"/abstracts-*.json
"$PY" "$S/export.py" L emb.npy names.json arxiv.json cites.json landmarks.json "$D"
cd "$SITE"   # the .mjs steps work on public/neurips relative to the site root
node "$REPO/scripts/neurips/build-api.mjs"
node "$REPO/scripts/neurips/stamp.mjs"
node "$REPO/scripts/check-neurips.mjs"
ls -la public/neurips/data | awk '{print $5, $9}'
