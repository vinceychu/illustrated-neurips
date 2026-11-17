# Illustrated NeurIPS paper: build, reproduce and check.
#
#   make check            numbers in main.tex == results/*.json (no data needed)
#   make reproduce        recompute every table/figure from the pipeline data
#   make pdf              build the PDF (needs TeX Live + latexmk)
#
# Data-dependent targets need NEURIPS_DATA=/path/to/pipeline/data (see README, "Data").

PYTHON ?= python3
PY := $(PYTHON) -m
NEURIPS_DATA ?= data
export NEURIPS_DATA

.PHONY: help pdf source reproduce stats sample figures clustering retrieval judge author-check \
        check test lint format clean

help:  ## list targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

pdf:  ## build main.pdf with latexmk
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

source:  ## LaTeX source archive for arXiv/Zenodo -> build/source.tar.gz
	mkdir -p build
	tar czf build/source.tar.gz main.tex neurips_2025.sty figures

reproduce: stats sample figures clustering retrieval author-check check  ## everything except the LLM judge

stats:  ## Section 3, Table 1 -> results/corpus_stats.json
	$(PY) eval.corpus_stats

sample:  ## items for Section 5.3 -> results/label_items.json, label/items.json
	$(PY) eval.sample_items

figures:  ## Figures 1-2, Table 5, citations/landmarks -> figures/, results/paper_figs.json
	$(PY) eval.figures

clustering:  ## Table 2 -> results/paper_eval.json
	$(PY) eval.clustering

retrieval:  ## Table 3 -> results/paper_eval.json (sentence-transformers; GPU recommended)
	$(PY) eval.retrieval

judge:  ## Table 4, LLM judge (needs an OpenAI-compatible endpoint: LLM_BASE_URL, LLM_MODEL)
	$(PY) eval.llm_judge

author-check:  ## Table 4, author subset -> results/human_labels.json, results/human_check.json
	$(PY) eval.author_check

check:  ## verify every reported number against results/
	$(PY) eval.check_numbers

test:  ## unit tests and consistency checks
	$(PYTHON) -m pytest

lint:  ## ruff lint + format check
	ruff check eval tools tests
	ruff format --check eval tools tests

format:  ## apply ruff fixes and formatting
	ruff check --fix eval tools tests
	ruff format eval tools tests

clean:  ## remove LaTeX and build artefacts
	latexmk -C main.tex 2>/dev/null || true
	rm -rf build .pytest_cache .ruff_cache
