"""Consistency checks that need no pipeline data (run in CI)."""

from __future__ import annotations

import json

import pytest

from eval import author_check, check_numbers, llm_judge
from eval.common import PAPER_DIR, RESULTS_DIR, cohen_kappa, load_json, wilson


def test_paper_numbers_match_results():
    assert check_numbers.main([]) == 0


def test_author_check_reproduces_committed_results():
    human_labels, check = author_check.run(RESULTS_DIR)
    assert human_labels == load_json(RESULTS_DIR / "human_labels.json")
    assert check == load_json(RESULTS_DIR / "human_check.json")
    assert json.dumps(check["pairs"]) == json.dumps(load_json(RESULTS_DIR / "human_check.json")["pairs"])


def test_author_labels_are_after_cutoff_and_topic_only():
    labels = load_json(RESULTS_DIR / "human_labels.json")["labels"]
    cutoff = author_check.cutoff_ms()
    items = {x["id"]: x for x in load_json(RESULTS_DIR / "label_items.json")}
    assert labels
    assert all(v["at"] >= cutoff and items[k]["kind"] == "topic" for k, v in labels.items())


def test_judge_summary_matches_items():
    run = load_json(RESULTS_DIR / "llm_judge.json")
    assert llm_judge.summarize(run["items"]) == run["summary"]
    assert run["model"] == "glm-5.3-flash"


def test_labelling_page_serves_the_sampled_items():
    page = (PAPER_DIR / "label" / "items.json").read_bytes()
    assert page == (RESULTS_DIR / "label_items.json").read_bytes()
    items = json.loads(page)
    assert sum(x["kind"] == "topic" for x in items) == 150
    assert sum(x["kind"] == "arxiv" for x in items) == 50


def test_control_jobs_are_deterministic():
    items = load_json(RESULTS_DIR / "label_items.json")
    topics = [{"name": f"topic {i}", "blurb": ""} for i in range(300)]
    jobs = llm_judge.build_jobs(items, topics)
    assert [j[1] for j in jobs[-50:]] == [r["id"] for r in load_json(RESULTS_DIR / "llm_judge.json")["items"][-50:]]


@pytest.mark.parametrize(
    ("k", "n", "lo", "hi"),
    [(90, 150, 52.0, 67.5), (130, 150, 80.3, 91.2), (50, 50, 92.9, 100.0), (32, 73, 33.0, 55.2)],
)
def test_wilson_matches_paper(k, n, lo, hi):
    assert [round(100 * x, 1) for x in wilson(k, n)] == [lo, hi]


def test_cohen_kappa_edge_cases():
    assert cohen_kappa("ab", "ab") == 1.0
    assert cohen_kappa(["yes", "no", "yes", "no"], ["no", "yes", "no", "yes"]) == pytest.approx(-1.0)
    with pytest.raises(ValueError):
        cohen_kappa([], [])
