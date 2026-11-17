# Illustrated NeurIPS: A Navigable Map of 30,225 NeurIPS Papers (2020–2026)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24301136.svg)](https://doi.org/10.5281/zenodo.24301136)
[![Paper PDF](https://img.shields.io/badge/paper-PDF-b31b1b.svg)](paper/Chu_2026_Illustrated_NeurIPS.pdf)
[![Live map](https://img.shields.io/badge/live-map-2b6cb0.svg)](https://vincentychu.com/neurips/)
[![CI](https://github.com/vinceychu/illustrated-neurips/actions/workflows/ci.yml/badge.svg)](https://github.com/vinceychu/illustrated-neurips/actions/workflows/ci.yml)
[![License: CC BY 4.0 / MIT](https://img.shields.io/badge/license-CC%20BY%204.0%20%2F%20MIT-lightgrey.svg)](LICENSE.md)

**Vincent Chu** · University of Michigan · [PDF](paper/Chu_2026_Illustrated_NeurIPS.pdf) ·
DOI [10.5281/zenodo.24301136](https://doi.org/10.5281/zenodo.24301136) (all versions; latest v6 =
[10.5281/zenodo.24312265](https://doi.org/10.5281/zenodo.24312265)) · Live map: <https://vincentychu.com/neurips/> 

> NeurIPS accepted 1,898 papers in 2020 and 9,111 in 2026. At that volume, reading the proceedings is no
> longer how researchers learn the shape of the field. We present *Illustrated NeurIPS*, an open dataset and
> browser-based map of all 30,225 papers accepted to NeurIPS from 2020 to 2026. Each paper is embedded from
> its title and abstract, placed on a two-dimensional map, and assigned to one of 285 fine topics nested in 30
> areas, each with a short name and one-sentence description. We link 21,946 papers (72.6%) to their arXiv
> records, attach citation counts to 26,172, and add 1,035 highly cited "landmark" papers from other venues to
> the topics they belong to. Against NeurIPS's own subject-area labels, our two-stage clustering (k-means on
> UMAP features) agrees better than k-means on the raw embeddings (adjusted Rand index 0.086 vs. 0.065;
> paired-bootstrap 95% interval of the gain [0.018, 0.023]) and much better than TF-IDF clustering (0.056).
> Title-only search over the deployed embeddings retrieves the correct paper first 83.2% of the time among
> 26,632 abstracts (MRR 0.876, vs. 0.761 for TF-IDF). The map shows, for example, that *LLM agent benchmarks*
> and *RL with verifiable rewards* went from no NeurIPS papers in 2020–21 to 1.5% and 1.1% of 2025–26 papers,
> while *generative adversarial networks* fell from 1.0% to 0.01%. The site, data and code are public.

## For agents / maintainers

1. Read `vinceychu/illustrated-neurips` on branch `main`, starting with [`paper/HANDOFF.md`](paper/HANDOFF.md). It has
   the status, the rules you must follow, where every file lives, and how to rebuild and publish. Also read
   `paper/README.md`.
2. The latest notes, the build machine and the location of the pipeline data are in the maintainers' private
   notes (notes topic `"neurips-paper"`), not in this repository. Rebuild the LaTeX with `make pdf` (latexmk)
   on a machine with TeX Live; cloud containers can't run TeX.
3. Published version: Zenodo concept DOI `10.5281/zenodo.24301136`. Updates go up as a **new version** through
   `paper/tools/zenodo_newversion.py`, never as a new record. The token stays in the maintainer's token file
   (`ZENODO_TOKEN_FILE`); never print it.

## Results at a glance

| Result | Value | Where | Produced by |
|---|---|---|---|
| Corpus | 30,225 papers, 285 topics in 30 areas | §3, Table 1 | `eval/corpus_stats.py` |
| arXiv linking | 21,946 papers (72.6%) | §3.2, Table 1 | `eval/corpus_stats.py` |
| Clustering vs NeurIPS labels | ARI 0.086 vs 0.065 (raw k-means), gain CI [0.018, 0.023] | §5.1, Table 2 | `eval/clustering.py` |
| Title-only search | R@1 83.2%, MRR 0.876 | §5.2, Table 3 | `eval/retrieval.py` |
| Topic fit (LLM judge, n=150) | 60.0% full, 86.7% at least partly | §5.3, Table 4 | `eval/llm_judge.py` |
| Topic fit (author, n=73) | 43.8% full, 83.6% at least partly; κ = 0.23 vs judge | §5.3, Table 4 | `eval/author_check.py` |
| Topic trends | LLM agent benchmarks 0 → 1.50%; GANs 1.02% → 0.01% | §6, Table 5 | `eval/figures.py` |

`make check` rebuilds every number above, and every other number in the paper's tables and text, from
`results/` and confirms it appears verbatim in `main.tex`.

## Repository layout

```
illustrated-neurips/
├── paper/                             the paper, its evaluation and results
│   ├── Chu_2026_Illustrated_NeurIPS.pdf   the paper (v6, identical to the latest Zenodo version)
│   ├── main.tex, neurips_2025.sty         LaTeX source (NeurIPS style, preprint mode)
│   ├── figures/                           Figure 1 (fig_map.pdf/.png) and Figure 2 (fig_years.pdf)
│   ├── eval/                              evaluation code: one CLI per table or figure
│   │   ├── corpus_stats.py                §3, Table 1          -> results/corpus_stats.json
│   │   ├── clustering.py                  §5.1, Table 2        -> results/paper_eval.json
│   │   ├── retrieval.py                   §5.2, Table 3        -> results/paper_eval.json
│   │   ├── sample_items.py                §5.3 sample          -> results/label_items.json
│   │   ├── llm_judge.py                   §5.3, Table 4        -> results/llm_judge.json
│   │   ├── author_check.py                §5.3, Table 4        -> results/human_{labels,check}.json
│   │   ├── figures.py                     Figs 1-2, Table 5    -> figures/, results/paper_figs.json
│   │   ├── check_numbers.py               main.tex vs results/ (data-free)
│   │   └── common.py                      paths, data loading, Wilson interval, Cohen's kappa
│   ├── results/                           committed outputs of eval/ (and the raw label export)
│   ├── label/                             the labelling page used for the checks (index.html, items.json)
│   ├── tests/                             data-free tests (run in CI)
│   ├── tools/zenodo_newversion.py         publish a new Zenodo version; zenodo_record.json = latest record
│   ├── Makefile, pyproject.toml, requirements*.txt
│   └── HANDOFF.md                         status, rules and release process
├── scripts/neurips/                   the map pipeline: corpus, arXiv matching, citations, embedding,
│                                      layout, naming, landmarks, export, static API
├── CITATION.cff, LICENSE.md
└── .github/workflows/ci.yml           lint, tests and the number check on every push
```

The map itself is built by the pipeline in [`scripts/neurips/`](scripts/neurips/) and served at
<https://vincentychu.com/neurips/>.

## Reproduce

```bash
cd paper
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Data-free: tests, lint, and every reported number against results/
make test lint check

# Full re-computation from the pipeline data (see "Data")
export NEURIPS_DATA=/path/to/pipeline/data
make reproduce        # stats, sample, figures, clustering, retrieval, author-check, check
make judge            # optional: re-runs the LLM judge (needs LLM_BASE_URL / LLM_MODEL)
make pdf              # needs TeX Live + latexmk
```

`make help` (in `paper/`) lists every target. Each script also runs on its own, e.g.
`python -m eval.clustering --data-dir "$NEURIPS_DATA"`, and takes `--help`.

**Verified.** Re-running the scripts on the pipeline data reproduces the committed `results/` exactly
(`label_items.json`, `paper_figs.json`, `paper_eval.json`, `human_check.json`) and the committed figures
(identical up to the PDF creation date, which the scripts no longer write). Retrieval embeds on a GPU, so
on other hardware the last digit of a metric may differ. The LLM judge is run at temperature 0 but depends
on the serving stack; its committed verdicts are the ones reported.

## Data

| Input (in `$NEURIPS_DATA`) | Contents | Built by |
|---|---|---|
| `L_laid.json` | one record per paper: year, title, abstract, topic, area, map position, subject label | `scripts/neurips/corpus.py` → `embed.py` → `layout.py` |
| `emb.npy` | bge-small-en-v1.5 embeddings (384-D, unit norm), row-aligned | `scripts/neurips/embed.py` |
| `names.json` | topic and area names and descriptions | `scripts/neurips/name.py` |
| `arxiv.json` | arXiv id, category, date and abstract per matched paper | `scripts/neurips/arxiv_match.py` |
| `cites.json` | citation counts (OpenAlex, Semantic Scholar) | `scripts/neurips/citations.py` |
| `landmarks.json` | landmark papers from other venues | `scripts/neurips/landmarks.py` |

Sources: the NeurIPS accepted-paper listings
(`https://neurips.cc/static/virtual/data/neurips-<year>-orals-posters.json`, 2020–2026), the arXiv API,
OpenAlex and Semantic Scholar (snapshot of November 2026). These intermediate files total about 400 MB and
are not committed; each pipeline script documents its inputs and outputs in its header. The released map
data (coordinates, topics, metadata, abstracts and int8 embeddings) and a static JSON API are served under
<https://vincentychu.com/neurips/>.

The topic-fit check uses `results/label_items.json` (150 topic and 50 arXiv items, seed 2026), the judge's
verdicts in `results/llm_judge.json`, and the author's labels from the labelling page,
`results/label_export_2026-11-17.json` (one document per item with its save time `at`; labels saved before
2026-11-17T07:31Z were made by an AI assistant and are excluded by `eval/author_check.py`).

## Cite

```bibtex
@misc{chu2026illustratedneurips,
  title  = {Illustrated {NeurIPS}: A Navigable Map of 30,225 {NeurIPS} Papers (2020--2026) with Linked {arXiv} Records, Citations and Landmark Papers},
  author = {Chu, Vincent},
  year   = {2026},
  doi    = {10.5281/zenodo.24301136},
  url    = {https://doi.org/10.5281/zenodo.24301136},
  note   = {Preprint}
}
```

GitHub's "Cite this repository" uses [`CITATION.cff`](CITATION.cff).

## License

The paper, figures and results are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this directory under the MIT License. See [`LICENSE`](LICENSE.md).
