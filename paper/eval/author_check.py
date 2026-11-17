"""The author's check of a subset of topic items (Section 5.3, Table 4, v6 onwards).

The labelling page (``label/``) saved one document per item with a millisecond
timestamp ``at``. Only topic labels saved at or after the cut-off are the author's;
earlier ones in the export were made by an AI assistant and are excluded. This script
selects those labels, compares them with the LLM judge on the same items and writes
``results/human_labels.json`` and ``results/human_check.json``.

Needs no pipeline data: it reads only ``results/``.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .common import base_parser, cohen_kappa, load_json, wilson, write_json

EXPORT = "label_export_2026-11-17.json"
CUTOFF_UTC = "2026-11-17T07:31:00Z"
VERDICTS = ("yes", "partly", "no")
NOTE = (
    "Author topic labels saved at or after 2026-11-17T07:31Z; earlier labels in the export were made by an AI "
    "assistant and are excluded."
)


def cutoff_ms(iso: str = CUTOFF_UTC) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(UTC).timestamp() * 1000)


def select_labels(export: dict, items: list[dict], cutoff: int) -> dict[str, dict]:
    """Author topic labels in item order: ``{id: {v, at, by}}``."""
    keep = {}
    for it in items:
        doc = export.get(it["id"])
        if it["kind"] == "topic" and doc and doc.get("kind") == "topic" and doc["at"] >= cutoff:
            keep[it["id"]] = {"v": doc["v"], "at": doc["at"], "by": doc.get("by")}
    return keep


def compare(labels: dict[str, dict], judge_items: list[dict]) -> dict:
    judge = {r["id"]: r["v"] for r in judge_items if r["kind"] == "topic"}
    ids = sorted(labels)  # string order, as in the published file
    human = [labels[i]["v"] for i in ids]
    glm = [judge[i] for i in ids]
    n = len(ids)
    hc, gc = Counter(human), Counter(glm)
    full, atleast = hc["yes"], hc["yes"] + hc["partly"]

    def pct(k: int) -> float:
        return round(100 * k / n, 1)

    def ci(k: int) -> list[float]:
        return [round(100 * x, 1) for x in wilson(k, n)]

    return {
        "n": n,
        "human": {v: hc[v] for v in VERDICTS},
        "glm_same": {v: gc[v] for v in VERDICTS},
        "human_full_pct": pct(full),
        "human_full_ci": ci(full),
        "human_atleast_pct": pct(atleast),
        "human_atleast_ci": ci(atleast),
        "glm_full_pct": pct(gc["yes"]),
        "glm_atleast_pct": pct(gc["yes"] + gc["partly"]),
        "exact_agree_pct": pct(sum(h == g for h, g in zip(human, glm, strict=True))),
        "kappa": round(cohen_kappa(human, glm), 2),
        "binary_agree_pct": pct(sum((h != "no") == (g != "no") for h, g in zip(human, glm, strict=True))),
        "pairs": dict(Counter(f"{h}|{g}" for h, g in zip(human, glm, strict=True))),
        "note": NOTE,
    }


def run(results_dir: Path) -> tuple[dict, dict]:
    export = load_json(results_dir / EXPORT)
    items = load_json(results_dir / "label_items.json")
    judge = load_json(results_dir / "llm_judge.json")["items"]
    labels = select_labels(export, items, cutoff_ms())
    human_labels = {"cutoff_utc": CUTOFF_UTC, "source": f"paper/results/{EXPORT}", "labels": labels}
    return human_labels, compare(labels, judge)


def main(argv: list[str] | None = None) -> None:
    args = base_parser(__doc__.splitlines()[0], data=False).parse_args(argv)
    human_labels, check = run(args.results_dir)
    write_json(args.results_dir / "human_labels.json", human_labels)
    write_json(args.results_dir / "human_check.json", check)
    print(
        f"{check['n']} author labels: full fit {check['human_full_pct']}% {check['human_full_ci']}, "
        f"at least partly {check['human_atleast_pct']}%, kappa vs judge {check['kappa']}"
    )


if __name__ == "__main__":
    main()
