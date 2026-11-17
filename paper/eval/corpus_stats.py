"""Corpus statistics (Section 3, Table 1 and the topic counts in Section 4).

Writes ``results/corpus_stats.json``.
"""

from __future__ import annotations

from collections import Counter

from .common import DataDir, arxiv_key, base_parser, write_json


def by_year(counter: Counter) -> dict[str, int]:
    return {str(k): v for k, v in sorted(counter.items())}


def corpus_stats(data: DataDir) -> dict:
    papers = data.papers()
    arxiv = data.json("arxiv.json")
    names = data.names()

    years = sorted({p["y"] for p in papers})
    n_year = Counter(p["y"] for p in papers)
    matched = [p for p in papers if arxiv.get(arxiv_key(p), {}).get("id")]
    m_year = Counter(p["y"] for p in matched)
    labelled = [p for p in papers if p.get("tp")]
    sizes = sorted(Counter(p["f"] for p in papers).values())

    return {
        "n_papers": len(papers),
        "papers_by_year": by_year(n_year),
        "presentation": dict(Counter(p.get("k") for p in papers).most_common()),
        "track": dict(Counter(p.get("tr") for p in papers).most_common()),
        "abstract_source": dict(Counter(p.get("abs") for p in papers).most_common()),
        "abstract_source_by_year": {
            str(y): dict(Counter(p.get("abs") for p in papers if p["y"] == y).most_common()) for y in years
        },
        "arxiv": {
            "n_matched": len(matched),
            "rate": round(len(matched) / len(papers), 4),
            "matched_by_year": by_year(m_year),
            "rate_by_year": {str(y): round(m_year[y] / n_year[y], 4) for y in years},
        },
        "subject_labels": {
            "n": len(labelled),
            "by_year": by_year(Counter(p["y"] for p in labelled)),
        },
        "topics": {
            "n_fine": len({p["f"] for p in papers}),
            "n_coarse": len({p["c"] for p in papers}),
            "n_fine_named": len(names["fine"]),
            "n_coarse_named": len(names["coarse"]),
            # upper median, as reported in the paper
            "fine_size": {"min": sizes[0], "median": sizes[len(sizes) // 2], "max": sizes[-1]},
        },
    }


def main(argv: list[str] | None = None) -> None:
    ap = base_parser(__doc__.splitlines()[0])
    args = ap.parse_args(argv)
    out = corpus_stats(DataDir(args.data_dir))
    path = write_json(args.results_dir / "corpus_stats.json", out)
    print(f"wrote {path}: {out['n_papers']} papers, arXiv match {out['arxiv']['rate']:.1%}")


if __name__ == "__main__":
    main()
