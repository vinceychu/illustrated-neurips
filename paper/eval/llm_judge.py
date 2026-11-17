"""Independent LLM judge for the topic-fit and arXiv-match checks (Section 5.3, Table 4).

The topic names were written by Claude, so a *different* model (GLM-5.3-Flash, served
locally) judges them; no model grades its own output. For every item in
``results/label_items.json`` the judge answers yes / partly / no. As a control, 50 topic
items are shown with a randomly chosen *wrong* topic (seed 7).

The judge is any OpenAI-compatible chat endpoint (e.g. vLLM)::

    LLM_BASE_URL=http://localhost:8000 LLM_MODEL=glm-5.3-flash python -m eval.llm_judge

Writes ``results/llm_judge.json``. ``--summarize`` only re-derives the summary and the
Wilson intervals from an existing file (no model calls).
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import os
import random
import urllib.request
from collections import Counter
from typing import Any

from .common import DataDir, base_parser, load_json, wilson, write_json

DEFAULT_MODEL = "glm-5.3-flash"
VERDICTS = ("yes", "partly", "no")
CONTROL_SEED, N_CONTROL = 7, 50
WORKERS, RETRIES = 6, 3

TOPIC_SYSTEM = (
    "You check a topic map of NeurIPS papers. Given a paper (title, abstract) and the topic it was placed under "
    '(name and one-sentence description), judge whether the topic describes the paper. Answer "yes" if the paper '
    'clearly belongs, "partly" if it is related but the topic misses its main contribution, "no" if it does not '
    'belong. Return JSON {"v": "yes"|"partly"|"no", "why": "<=15 words"}.'
)
ARXIV_SYSTEM = (
    'Decide whether two abstracts describe the same paper. "yes" = same paper (wording may differ slightly), '
    '"partly" = same work but a clearly different version (e.g. extended or retitled), "no" = different papers. '
    'Return JSON {"v": "yes"|"partly"|"no", "why": "<=15 words"}.'
)


def topic_prompt(item: dict, topic: str, blurb: str) -> str:
    return f"Paper: {item['t']}\nAbstract: {item['ab']}\n\nPlaced under topic: {topic}\nTopic description: {blurb}"


def arxiv_prompt(item: dict) -> str:
    return (
        f"Title: {item['t']}\n\nAbstract A (NeurIPS): {item['ab']}\n\nAbstract B (arXiv {item['ax']}): {item['axab']}"
    )


def chat(prompt: str, system: str, *, base_url: str, model: str, max_tokens: int = 120) -> str:
    """One deterministic (temperature 0) JSON-mode completion, thinking disabled."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt + "\n/nothink"}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        json.dumps(payload).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return (json.load(r)["choices"][0]["message"].get("content") or "").strip()


def ask(system: str, prompt: str, **kw: Any) -> dict:
    for _ in range(RETRIES):
        try:
            answer = json.loads(chat(prompt, system, **kw))
            if answer.get("v") in VERDICTS:
                return answer
        except Exception:
            pass
    return {"v": "error", "why": "unparsed"}


def build_jobs(items: list[dict], fine_topics: list[dict]) -> list[tuple[str, str, str, str]]:
    """``(kind, item id, system prompt, user prompt)`` for every judgement."""
    jobs = []
    for it in items:
        if it["kind"] == "topic":
            jobs.append(("topic", it["id"], TOPIC_SYSTEM, topic_prompt(it, it["topic"], it["blurb"])))
        else:
            jobs.append(("arxiv", it["id"], ARXIV_SYSTEM, arxiv_prompt(it)))
    rnd = random.Random(CONTROL_SEED)
    for it in rnd.sample([x for x in items if x["kind"] == "topic"], N_CONTROL):
        wrong = rnd.choice([f for f in fine_topics if f["name"] != it["topic"]])
        jobs.append(("control", it["id"], TOPIC_SYSTEM, topic_prompt(it, wrong["name"], wrong["blurb"])))
    return jobs


def summarize(results: list[dict]) -> dict[str, dict[str, int]]:
    return {k: dict(Counter(r["v"] for r in results if r["kind"] == k)) for k in ("topic", "arxiv", "control")}


def intervals(summary: dict[str, dict[str, int]]) -> dict[str, list[float]]:
    """Wilson 95% intervals (in %) quoted in the caption of Table 4."""
    t, a = summary["topic"], summary["arxiv"]
    n_t, n_a = sum(t.values()), sum(a.values())

    def pct(k: int, n: int) -> list[float]:
        return [round(100 * x, 1) for x in wilson(k, n)]

    return {
        "topic_full": pct(t.get("yes", 0), n_t),
        "topic_at_least_partly": pct(t.get("yes", 0) + t.get("partly", 0), n_t),
        "arxiv_precision": pct(a.get("yes", 0), n_a),
    }


def main(argv: list[str] | None = None) -> None:
    ap = base_parser(__doc__.splitlines()[0])
    ap.add_argument("--summarize", action="store_true", help="recompute the summary of an existing run only")
    ap.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL", "http://localhost:8000"))
    ap.add_argument("--model", default=os.environ.get("LLM_MODEL", DEFAULT_MODEL))
    args = ap.parse_args(argv)
    out_path = args.results_dir / "llm_judge.json"

    if args.summarize:
        run = load_json(out_path)
        print(json.dumps({"summary": summarize(run["items"]), "wilson_pct": intervals(run["summary"])}, indent=1))
        return

    items = load_json(args.results_dir / "label_items.json")
    fine_topics = list(DataDir(args.data_dir).names()["fine"].values())
    jobs = build_jobs(items, fine_topics)
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        answers = ex.map(lambda j: ask(j[2], j[3], base_url=args.base_url, model=args.model), jobs)
        results = [dict(kind=kind, id=iid, **ans) for (kind, iid, _, _), ans in zip(jobs, answers, strict=True)]
    summary = summarize(results)
    write_json(out_path, dict(model=args.model, summary=summary, items=results))
    print(json.dumps(summary))
    for r in results:
        if r["kind"] in ("topic", "arxiv") and r["v"] != "yes":
            print(r["kind"][0].upper(), r["v"], r["id"], r["why"])


if __name__ == "__main__":
    main()
