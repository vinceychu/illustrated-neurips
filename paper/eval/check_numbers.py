"""Check that every number the paper reports matches the committed results.

Rebuilds each reported table row and in-text figure from ``results/*.json`` as the
exact LaTeX string the paper should contain, then looks for it in ``main.tex``.
Exits non-zero and lists the mismatches if any is missing. Needs no pipeline data.

    python -m eval.check_numbers            # from paper/
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .common import PAPER_DIR, base_parser, load_json
from .llm_judge import intervals

YEARS = [str(y) for y in range(2020, 2027)]


def n(x: int) -> str:
    """Integer as written in the paper: ``30{,}225``."""
    return f"{x:,}".replace(",", "{,}")


def f3(x: float) -> str:
    """Three decimals, rounding half up from the stored four-decimal value (as in the paper)."""
    return str(Decimal(str(x)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def pct(k: int, total: int, nd: int = 1) -> str:
    return "100" if k == total else f"{100 * k / total:.{nd}f}"


def row(*cells: str) -> str:
    return " & ".join(cells) + r" \\"


def corpus_checks(cs: dict) -> Iterator[tuple[str, str]]:
    ax, by = cs["arxiv"], cs["papers_by_year"]
    yield "Table 1, papers", row("Papers", *(n(by[y]) for y in YEARS), n(cs["n_papers"]))
    yield (
        "Table 1, arXiv match",
        row(
            r"arXiv match (\%)",
            *(pct(ax["matched_by_year"][y], by[y]) for y in YEARS),
            pct(ax["n_matched"], cs["n_papers"]),
        ),
    )
    sl = cs["subject_labels"]
    yield (
        "Table 1, subject labels",
        row("NeurIPS subject label", *(n(sl["by_year"][y]) if y in sl["by_year"] else "--" for y in YEARS), n(sl["n"])),
    )
    pr, tr = cs["presentation"], cs["track"]
    yield (
        "corpus composition",
        (
            f"{n(pr['poster'])} posters, {n(pr['spotlight'])} spotlights and {n(pr['oral'])} orals; "
            f"{n(tr['Main'])} main-track, {n(tr['D&B'])} Datasets \\& Benchmarks, {n(tr['Journal'])} journal-track "
            f"and {n(tr['Position'])} position papers"
        ),
    )
    src26 = cs["abstract_source_by_year"]["2026"]
    yield "2026 abstracts from arXiv", f"({n(src26['arxiv'])} papers)"
    yield "2026 title-only papers", f"The remaining {n(src26[''])} 2026 papers"
    no_match_2026 = by["2026"] - ax["matched_by_year"]["2026"]
    yield "Limitations, 2026", f"{n(src26[''])} have titles only, and {pct(no_match_2026, by['2026'])}\\% have no arXiv"
    link = f"{n(ax['n_matched'])} papers ({pct(ax['n_matched'], cs['n_papers'])}\\%)"
    yield "abstract, arXiv linking", f"We link {link}"
    yield "Section 3.2, arXiv linking", f"Overall {link} match"
    t = cs["topics"]
    fs = t["fine_size"]
    yield "fine topics", f"{t['n_fine']} fine topics (median {fs['median']} papers; range {fs['min']}--{fs['max']})"
    yield "abstract, topics", f"{t['n_fine']} fine topics nested in {t['n_coarse']} areas"


def figs_checks(pf: dict, n_fine: int) -> Iterator[tuple[str, str]]:
    c, lm = pf["cites"], pf["landmarks"]
    yield "citations, OpenAlex", f"covers {n(c['oa'])} papers"
    yield (
        "citations, coverage",
        (
            f"{n(c['n_entries'])} papers have at least one source and {n(c['n_with'])} have one or more citations "
            f"(median over papers with a source: {c['median']:g})"
        ),
    )
    venues = dict(lm["venues"])
    yield (
        "landmarks",
        (
            f"{n(lm['n'])} landmarks in {lm['topics']} of the {n_fine} topics "
            f"(median {lm['median_cites']:g} citations), "
            f"led by arXiv-only papers ({venues['arXiv']}), ICLR ({venues['ICLR']}), CVPR ({venues['CVPR']}) "
            f"and ICML ({venues['ICML']})"
        ),
    )
    yield "Limitations, topics without landmarks", f"({n_fine - lm['topics']} of {n_fine} topics do not)"
    for label, rows, k in (("riser", pf["risers"], 5), ("faller", pf["fallers"], 4)):
        for name, early, late, s_early, s_late in rows[:k]:
            yield f"Table 5, {label} {name}", row(name, str(early), str(late), f"{s_early:.2f}", f"{s_late:.2f}")
    r, f = pf["risers"], pf["fallers"]
    yield (
        "abstract, trends",
        (
            f"to {r[0][4]:.1f}\\% and {r[1][4]:.1f}\\% of 2025--26 papers, "
            f"while \\emph{{generative adversarial networks}} "
            f"fell from {f[0][3]:.1f}\\% to {f[0][4]:.2f}\\%"
        ),
    )


def eval_checks(pe: dict, topics: dict) -> Iterator[tuple[str, str]]:
    cl, bs, lb = pe["cluster_v2"], pe["bootstrap_ours_minus_kmeans"], pe["labels_v2"]
    metrics = ("nmi_fine", "ari_fine", "nmi_coarse", "ari_coarse")

    def cells(m: str) -> list[str]:
        return [f3(cl[m][k]) for k in metrics]

    yield "Table 2, random", row("Random", *cells("random"))
    yield "Table 2, TF-IDF", row("TF-IDF + LSA + k-means", *cells("tfidf_lsa"))
    yield "Table 2, k-means s0", row("k-means, embeddings (seed 0)", *cells("kmeans_raw_s0"))
    yield (
        "Table 2, k-means s1/s2",
        row(
            "k-means, embeddings (seeds 1, 2)",
            *(f"{f3(cl['kmeans_raw_s1'][k])}, {f3(cl['kmeans_raw_s2'][k])}" for k in metrics),
        ),
    )
    yield "Table 2, ours", row(r"\textbf{Ours} (UMAP k-means, Ward)", *(rf"\textbf{{{c}}}" for c in cells("ours")))
    yield "Table 2, gain", row(r"Ours $-$ k-means s0, mean", *(f"+{bs[k]['mean']:.3f}" for k in metrics))
    yield (
        "Table 2, bootstrap CI",
        row(r"\quad 95\% paired-bootstrap interval", *(f"[{f3(bs[k]['lo'])}, {f3(bs[k]['hi'])}]" for k in metrics)),
    )
    yield (
        "Table 2 caption",
        (
            f"{n(lb['n'])} papers (2023--2026): {topics['n_fine']} fine topics vs.\\ {lb['n_full']} fine labels, and "
            f"{topics['n_coarse']} areas vs.\\ {lb['n_top']} top-level labels"
        ),
    )
    yield "Section 5.1, labels", f"{n(lb['n'])} papers. Labels appear"
    yield "Section 5.1, label counts", f"there are {lb['n_full']} distinct fine labels and {lb['n_top']} top-level"
    yield (
        "abstract, clustering",
        (
            f"adjusted Rand index {f3(cl['ours']['ari_fine'])} vs.\\ {f3(cl['kmeans_raw_s0']['ari_fine'])}; "
            f"paired-bootstrap 95\\% interval of the gain $[{f3(bs['ari_fine']['lo'])}, {f3(bs['ari_fine']['hi'])}]$"
        ),
    )
    yield "abstract, TF-IDF clustering", f"TF-IDF clustering ({f3(cl['tfidf_lsa']['ari_fine'])})"
    seeds = sorted(cl[f"kmeans_raw_s{s}"]["ari_fine"] for s in range(3))
    yield "Section 5.1, seed variation", f"(ARI {f3(seeds[0])}--{f3(seeds[-1])} at the fine level)"

    rt = pe["retrieval"]
    yield "Table 3 caption", f"{n(pe['retrieval_n_docs'])} abstracts ({n(pe['retrieval_n_queries'])} queries)"

    def search(k: str) -> list[str]:
        return [f3(rt[k][m]) for m in ("mrr", "r1", "r10", "r100")]

    yield "Table 3, TF-IDF", row("TF-IDF (cosine)", *search("tfidf_title_to_abstract"))
    yield "Table 3, bge plain", row("bge-small, plain query", *search("bge_small_title_to_abstract"))
    yield "Table 3, hybrid", row("bge-small + TF-IDF, z-score sum", *search("hybrid_bge_tfidf"))
    d = search("bge_small_title_to_abstract_instr")
    yield (
        "Table 3, deployed",
        row(r"\textbf{bge-small with retrieval instruction (deployed)}", *(rf"\textbf{{{c}}}" for c in d[:3]), d[3]),
    )
    dep = rt["bge_small_title_to_abstract_instr"]
    yield (
        "abstract, search",
        (
            f"{100 * dep['r1']:.1f}\\% of the time among {n(pe['retrieval_n_docs'])} abstracts "
            f"(MRR {f3(dep['mrr'])}, vs.\\ {f3(rt['tfidf_title_to_abstract']['mrr'])} for TF-IDF)"
        ),
    )
    yield (
        "Section 5.2, search",
        f"first {100 * dep['r1']:.1f}\\% of the time and in the top 10 for {100 * dep['r10']:.1f}\\%",
    )


def judge_checks(jd: dict, hc: dict | None) -> Iterator[tuple[str, str]]:
    s = jd["summary"]

    def counts(c: dict) -> list[str]:
        tot = sum(c.values())
        return [f"{c[v]} ({pct(c[v], tot)}\\%)" if c.get(v) else "0" for v in ("yes", "partly", "no")]

    t, a = s["topic"], s["arxiv"]
    yield "Table 4, topic", row(f"Assigned topic fits the paper ($n={sum(t.values())}$)", *counts(t))
    yield (
        "Table 4, control",
        row(f"Control: random wrong topic ($n={sum(s['control'].values())}$)", *counts(s["control"])),
    )
    yield "Table 4, arXiv", row(f"arXiv record is the same paper ($n={sum(a.values())}$)", *counts(a))
    w = intervals(s)

    def span(lo_hi: list[float]) -> str:
        return "--".join(f"{x:g}" if x == 100 else f"{x:.1f}" for x in lo_hi)

    yield (
        "Table 4 caption, Wilson",
        (
            f"topic fits fully {span(w['topic_full'])}\\%, at least partly {span(w['topic_at_least_partly'])}\\%; "
            f"arXiv precision {span(w['arxiv_precision'])}\\%"
        ),
    )
    n_t = sum(t.values())
    full, part = t.get("yes", 0), t.get("yes", 0) + t.get("partly", 0)
    yield (
        "Section 5.3, judge",
        f"fits fully for {pct(full, n_t, 0)}\\% of papers and at least partly for {pct(part, n_t, 0)}\\%",
    )
    if hc is None:
        return
    m = hc["n"]
    yield "Table 4, author", row(f"Author, assigned topic fits ($n={m}$, subset)", *counts(hc["human"]))
    yield "Table 4, judge on author subset", row(f"LLM judge on the same {m} papers", *counts(hc["glm_same"]))
    lo, hi = hc["human_full_ci"]
    alo, ahi = hc["human_atleast_ci"]
    yield (
        "Section 5.3, author",
        (
            f"fits fully for {hc['human_full_pct']}\\% of these papers "
            f"(Wilson 95\\% interval {lo}--{hi}\\%) and at least "
            f"partly for {hc['human_atleast_pct']}\\% ({alo}--{ahi}\\%), against {hc['glm_full_pct']}\\% and "
            f"{hc['glm_atleast_pct']}\\% from the judge"
        ),
    )
    yield (
        "Section 5.3, agreement",
        (
            f"agree exactly on {hc['exact_agree_pct']}\\% of items "
            f"(Cohen's $\\kappa = {hc['kappa']:.2f}$) and on whether "
            f"the topic fits at all on {hc['binary_agree_pct']}\\%"
        ),
    )
    yield "Limitations, author", f"({hc['human_full_pct']}\\% full fit, {hc['human_atleast_pct']}\\% at least partial)"


def all_checks(results: Path) -> Iterator[tuple[str, str]]:
    cs = load_json(results / "corpus_stats.json")
    yield from corpus_checks(cs)
    yield from figs_checks(load_json(results / "paper_figs.json"), cs["topics"]["n_fine"])
    yield from eval_checks(load_json(results / "paper_eval.json"), cs["topics"])
    hc_path = results / "human_check.json"
    yield from judge_checks(load_json(results / "llm_judge.json"), load_json(hc_path) if hc_path.exists() else None)


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.splitlines()[0], data=False)
    ap.add_argument("--tex", type=Path, default=PAPER_DIR / "main.tex")
    ap.add_argument("-v", "--verbose", action="store_true", help="print every check")
    args = ap.parse_args(argv)
    tex = " ".join(args.tex.read_text(encoding="utf-8").split())
    checks = list(all_checks(args.results_dir))
    missing = [(label, frag) for label, frag in checks if " ".join(frag.split()) not in tex]
    for label, frag in checks if args.verbose else missing:
        status = "MISSING" if (label, frag) in missing else "ok"
        print(f"{status:7s} {label}: {frag}")
    print(f"{len(checks) - len(missing)}/{len(checks)} reported numbers match results/")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
