"""Draw the items for the topic-fit and arXiv-match checks (Section 5.3).

* 150 ``topic`` items: papers with abstracts, stratified by year in proportion to
  each year's share, shown with the topic they were placed under.
* 50 ``arxiv`` items: arXiv-matched papers from 2020-2025, shown with both abstracts.

Item ids are ``t<index>`` / ``a<index>`` into ``L_laid.json``. Seed 2026.
Writes ``results/label_items.json`` (also served to the labelling page as
``label/items.json``).
"""

from __future__ import annotations

import random
import shutil

from .common import PAPER_DIR, DataDir, arxiv_key, base_parser, write_json

SEED = 2026
N_TOPIC, N_ARXIV = 150, 50
MAX_ARXIV_YEAR = 2025


def sample_items(data: DataDir) -> list[dict]:
    papers, names, arxiv = data.papers(), data.names(), data.json("arxiv.json")
    rnd = random.Random(SEED)

    def fine(f: int) -> dict:
        return names["fine"].get(str(f), {})

    def coarse(c: int) -> dict:
        return names["coarse"].get(str(c), {})

    with_abstract = [i for i, p in enumerate(papers) if p["ab"]]
    by_year: dict[int, list[int]] = {}
    for i in with_abstract:
        by_year.setdefault(papers[i]["y"], []).append(i)
    pick: list[int] = []
    for _, idx in sorted(by_year.items()):
        pick += rnd.sample(idx, max(1, round(N_TOPIC * len(idx) / len(with_abstract))))

    items = []
    for i in pick[:N_TOPIC]:
        p = papers[i]
        items.append(
            dict(
                id=f"t{i}",
                kind="topic",
                y=p["y"],
                t=p["t"],
                ab=p["ab"][:700],
                topic=fine(p["f"]).get("name", ""),
                blurb=fine(p["f"]).get("blurb", ""),
                area=coarse(p["c"]).get("name", ""),
            )
        )

    matched = [
        i
        for i, p in enumerate(papers)
        if p["y"] <= MAX_ARXIV_YEAR and arxiv.get(arxiv_key(p), {}).get("id") and p["ab"]
    ]
    for i in rnd.sample(matched, N_ARXIV):
        p = papers[i]
        a = arxiv[arxiv_key(p)]
        items.append(
            dict(
                id=f"a{i}",
                kind="arxiv",
                y=p["y"],
                t=p["t"],
                ab=p["ab"][:500],
                ax=a["id"],
                axab=(a.get("ab") or "")[:500],
            )
        )
    return items


def main(argv: list[str] | None = None) -> None:
    ap = base_parser(__doc__.splitlines()[0])
    ap.add_argument("--no-page-copy", action="store_true", help="do not update label/items.json")
    args = ap.parse_args(argv)
    items = sample_items(DataDir(args.data_dir))
    path = write_json(args.results_dir / "label_items.json", items, indent=None, ensure_ascii=False)
    if not args.no_page_copy:
        shutil.copyfile(path, PAPER_DIR / "label" / "items.json")
    n_topic = sum(x["kind"] == "topic" for x in items)
    print(f"wrote {path}: {n_topic} topic + {len(items) - n_topic} arXiv items")


if __name__ == "__main__":
    main()
