# Maintaining the paper

Read this before changing anything in `paper/`, whether you are a person or an agent. It covers the
current status, the rules every change must follow, and how to rebuild and publish. Layout, data and
reproduction commands are in [`README.md`](README.md). Maintainer-only operational notes (machines,
accounts, credential locations) are kept privately and are not part of this repository.

## Status

| | |
|---|---|
| Paper | **v7**, `Chu_2026_Illustrated_NeurIPS.pdf` (7 pages, NeurIPS style in `preprint` mode), byte-identical to the latest Zenodo version. v7 points the code link at the public repository; v6 added the author's check of 73 topic items to Section 5.3 / Table 4. |
| Zenodo | Concept DOI (cite this; it resolves to the latest version) [10.5281/zenodo.24301136](https://doi.org/10.5281/zenodo.24301136). Latest record: `tools/zenodo_record.json`. |
| arXiv | Not yet posted. |
| Public code | [github.com/vinceychu/illustrated-neurips](https://github.com/vinceychu/illustrated-neurips) (cited in the paper since v7): this repository: the paper, its evaluation and the map pipeline. The maintainers keep a working copy in the (private) website repository and land every change in both. |

Versions: v1 24301137, v2 24301266, v3 24301284, v4 24311529, v5 24311644 (same content as v4),
v6 24312265, v7 24313556 (latest, [10.5281/zenodo.24313556](https://doi.org/10.5281/zenodo.24313556)). Record 24311587 is an erroneous intermediate version that reported AI-made labels as
the author's; it was superseded by v5 within minutes and must not be cited.

| Version | Change |
|---|---|
| v2, v3 | Float spacing and the availability list |
| v4 (= v5) | Removed the "author check" of v1–v3 (those labels were AI-made), the "Use of AI tools" section and timing wording; arXiv-match precision is estimated by the LLM judge, not by hand |
| v6 | Author check restored from the 73 topic labels the author saved (see rule 3) |
| v7 | Code link points to the public repository github.com/vinceychu/illustrated-neurips (record's software link and description updated too); no other text or number changes |

## Rules

1. **AI is not human.** Never present model output as human evaluation. The LLM judge (GLM-5.3-Flash) is
   reported as a model.
2. **No self-grading.** Claude named the topics, so Claude must never judge them.
3. **Author labels.** Only topic labels saved on the labelling page at or after **2026-11-17T07:31Z** are the
   author's (73 items). Earlier labels in `results/label_export_2026-11-17.json` were written by an AI
   assistant in the author's browser session, so the account field cannot tell them apart; only the `at`
   timestamp can. `eval/author_check.py` applies the cut-off; keep the raw export with timestamps so it can
   be audited.
4. **Report what comes out,** including unflattering numbers (full topic fit is 44–60%).
5. **No NeurIPS claims.** The NeurIPS style is used in `preprint` mode. Never switch to `final`, and never
   claim the paper was submitted to or accepted at NeurIPS.
6. **Numbers come from `results/`.** `make check` must pass: every number in `main.tex` is rebuilt from the
   committed results and matched against the source. Change a result and the text together, never one alone.
7. **Zenodo: new versions only.** Updates go up as a new version of the concept record through
   `tools/zenodo_newversion.py`, never as a new record. Never print or commit the token.
8. **Nothing personal in `paper/`** beyond what the PDF itself prints (author name, affiliation, email).
   Hosts, home paths, accounts and agent notes belong in the maintainers' private notes.

## Rebuild the PDF

```bash
cd paper
make pdf                                        # latexmk -> main.pdf (7 pages, no warnings)
cp main.pdf Chu_2026_Illustrated_NeurIPS.pdf    # only when releasing a new version
```

Needs TeX Live with `latexmk`; most cloud containers cannot run TeX. The arXiv/Zenodo source archive is
`make source` (`main.tex`, `neurips_2025.sty`, `figures/`).

## Publish a new version

1. Change `main.tex` (and `results/` via the scripts if numbers change); `make check test` must pass.
2. Rebuild the PDF, copy it to `Chu_2026_Illustrated_NeurIPS.pdf`, open a pull request and merge it.
3. `make source && python tools/zenodo_newversion.py <latest record id> v<N>` creates a draft;
   add `--publish` to publish it (it also sets the PDF as the default preview; `--code-url` sets the code link). The token comes from `ZENODO_TOKEN` or `ZENODO_TOKEN_FILE`.
4. Commit the updated `tools/zenodo_record.json`, the version line in `README.md`, and this file's status.
5. Check that the record page and the PDF URL open, and that the PDF previews on the record page.

## Adding labels or judges

- **More author labels:** export the labelling page's `labels` collection with timestamps, add it to
  `results/`, point `eval/author_check.py` at it and keep only labels the author saved (rule 3).
  Recompute with `make author-check`, update Section 5.3 and Table 4, then `make check`.
- **A second AI judge:** report agreement with GLM (Cohen's kappa) as a second *model* judge; never as human.

## Key numbers (all in the paper; `make check` verifies them)

- Corpus: 30,225 papers (2020–2026); 285 topics in 30 areas.
- Linking: arXiv match 72.6% (21,946 papers); citation counts for 26,172; 1,035 landmarks in 213 topics.
- Clustering vs NeurIPS labels: ARI 0.086 vs 0.065 for raw k-means (paired-bootstrap CI of the gain [0.018, 0.023]).
- Search: MRR 0.876, R@1 83.2%.
- LLM judge: topic fits 60% fully, 87% at least partly; 92% of wrong topics rejected; arXiv matches 50/50.
- Author (73 items): 43.8% full fit, 83.6% at least partly; kappa 0.23 with the LLM judge.
