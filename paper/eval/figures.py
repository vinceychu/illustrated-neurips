"""Figures 1-2, the trends table (Table 5) and citation/landmark statistics (Section 3).

Writes ``figures/fig_map.{pdf,png}``, ``figures/fig_years.pdf`` and
``results/paper_figs.json``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from .common import FIGURES_DIR, DataDir, Paper, base_parser, write_json

N_AREAS = 30
EARLY, LATE = (2020, 2021), (2025, 2026)
PDF_METADATA = {"CreationDate": None}  # byte-reproducible PDFs


def area_colours(n: int = N_AREAS) -> list:
    import matplotlib.pyplot as plt

    tab20, tab20b = plt.get_cmap("tab20"), plt.get_cmap("tab20b")
    return [tab20(i % 20) if i < 20 else tab20b(i % 20) for i in range(n)]


def plot_map(papers: Sequence[Paper], landmarks: list[dict], names: dict, out_dir: Path) -> None:
    """Figure 1: every paper on the 2D map coloured by area, with landmark papers."""
    import matplotlib.pyplot as plt

    x = np.array([p["x"] for p in papers])
    y = np.array([p["y2"] for p in papers])
    c = np.array([p["c"] for p in papers])
    cols = area_colours()
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(x, y, s=0.6, c=[cols[k] for k in c], linewidths=0, alpha=0.7, rasterized=True)
    ax.scatter(
        [lm["x"] for lm in landmarks],
        [lm["y2"] for lm in landmarks],
        s=6,
        marker="D",
        facecolors="none",
        edgecolors="k",
        linewidths=0.4,
        label="landmark papers (other venues)",
    )
    for k in range(N_AREAS):
        m = c == k
        ax.text(
            np.median(x[m]),
            np.median(y[m]),
            names["coarse"][str(k)]["name"],
            fontsize=5.5,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75),
        )
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines[:].set_visible(False)
    ax.legend(loc="lower left", fontsize=6, frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_map.pdf", dpi=300, metadata=PDF_METADATA)
    fig.savefig(out_dir / "fig_map.png", dpi=160)
    plt.close(fig)


def plot_years(papers: Sequence[Paper], names: dict, out_dir: Path) -> None:
    """Figure 2: accepted papers per year, stacked by the six largest areas."""
    import matplotlib.pyplot as plt

    years = sorted({p["y"] for p in papers})
    cols = area_colours()
    top = [k for k, _ in Counter(p["c"] for p in papers).most_common(6)]
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    bottom = np.zeros(len(years))
    for k in [*top, "other"]:
        counts = np.array(
            [
                sum(1 for p in papers if p["y"] == yy and (p["c"] == k if k != "other" else p["c"] not in top))
                for yy in years
            ]
        )
        ax.bar(
            years,
            counts,
            bottom=bottom,
            color=cols[k] if k != "other" else "#bbbbbb",
            label=names["coarse"][str(k)]["name"] if k != "other" else "Other",
            width=0.75,
        )
        bottom += counts
    ax.set_ylabel("Accepted papers")
    ax.legend(fontsize=4.8, frameon=False, ncol=1, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_dir / "fig_years.pdf", metadata=PDF_METADATA)
    plt.close(fig)


def topic_trends(papers: Sequence[Paper], names: dict) -> dict[str, list]:
    """Table 5: fine topics whose share of papers rose / fell most from 2020-21 to 2025-26.

    Rows are ``[name, papers 2020-21, papers 2025-26, share % 2020-21, share % 2025-26]``.
    Risers need at least 40 papers in total, fallers at least 30 in 2020-21.
    """
    early = [p for p in papers if p["y"] <= EARLY[1]]
    late = [p for p in papers if p["y"] >= LATE[0]]
    fe, fl = Counter(p["f"] for p in early), Counter(p["f"] for p in late)
    share = {f: (fl[f] / len(late), fe[f] / len(early)) for f in set(fe) | set(fl)}
    ratio = sorted(share, key=lambda f: (share[f][0] + 1e-4) / (share[f][1] + 1e-4))

    def row(f: int) -> list:
        name = names["fine"][str(f)]["name"]
        return [name, fe[f], fl[f], round(share[f][1] * 100, 2), round(share[f][0] * 100, 2)]

    risers = [row(f) for f in ratio[::-1][:8] if fe[f] + fl[f] >= 40][:6]
    fallers = [row(f) for f in ratio if fe[f] >= 30][:6]
    return {"risers": risers, "fallers": fallers}


def citation_stats(cites: dict) -> dict:
    entries = [v for v in cites.values() if isinstance(v, dict)]
    counts = [v["c"] for v in entries if "c" in v]
    return {
        "n_with": sum(1 for v in counts if v > 0),
        "n_entries": len(counts),
        "median": float(np.median(counts)),
        "oa": sum(1 for v in entries if "oa" in v),
        "s2": sum(1 for v in entries if "s2" in v),
    }


def landmark_stats(landmarks: list[dict]) -> dict:
    return {
        "n": len(landmarks),
        "topics": len({lm["f"] for lm in landmarks}),
        "venues": Counter(lm["venue"] for lm in landmarks).most_common(10),
        "median_cites": float(np.median([lm["cc"] for lm in landmarks])),
        "years": dict(sorted(Counter(lm["y"] for lm in landmarks).items())),
    }


def run(data: DataDir, fig_dir: Path | None) -> dict:
    papers, names = data.papers(), data.names()
    landmarks = data.json("landmarks.json")
    if fig_dir is not None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.rcParams.update(
            {"font.family": "DejaVu Sans", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False}
        )
        fig_dir.mkdir(parents=True, exist_ok=True)
        plot_map(papers, landmarks, names, fig_dir)
        plot_years(papers, names, fig_dir)
    return {
        **topic_trends(papers, names),
        "cites": citation_stats(data.json("cites.json")),
        "landmarks": landmark_stats(landmarks),
        "coarse_names": {k: v["name"] for k, v in names["coarse"].items()},
        "example_fine": [names["fine"][str(i)] for i in (0, 50, 100, 150, 200)],
    }


def main(argv: list[str] | None = None) -> None:
    ap = base_parser(__doc__.splitlines()[0])
    ap.add_argument("--fig-dir", type=Path, default=FIGURES_DIR, help="output directory for figures")
    ap.add_argument("--no-figures", action="store_true", help="only write paper_figs.json")
    args = ap.parse_args(argv)
    out = run(DataDir(args.data_dir), None if args.no_figures else args.fig_dir)
    path = write_json(args.results_dir / "paper_figs.json", out, default=str)
    print(f"wrote {path}" + ("" if args.no_figures else f" and figures in {args.fig_dir}"))


if __name__ == "__main__":
    main()
