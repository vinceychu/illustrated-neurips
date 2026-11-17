"""Shared helpers: paths, data loading, JSON I/O and small statistics.

The heavy inputs (about 400 MB) are produced by the map pipeline in
``scripts/neurips/`` and are not committed. Point the scripts at them with
``--data-dir`` or the ``NEURIPS_DATA`` environment variable. The directory must
contain:

=================  ==========================================================
``L_laid.json``    one record per paper (see :class:`Paper`), in pipeline order
``emb.npy``        bge-small-en-v1.5 embeddings, row-aligned with ``L_laid.json``
``names.json``     ``{"fine": {id: {name, blurb}}, "coarse": {id: {name, ...}}}``
``arxiv.json``     ``{"<year>|<title>": {id, cat, date, ab}}``
``cites.json``     ``{"<year>|<title>": {c, oa?, s2?}}``
``landmarks.json`` list of landmark papers placed on the map
=================  ==========================================================
"""

from __future__ import annotations

import argparse
import json
import math
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, NotRequired, TypedDict

PAPER_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PAPER_DIR / "results"
FIGURES_DIR = PAPER_DIR / "figures"
DATA_ENV = "NEURIPS_DATA"


class Paper(TypedDict):
    """One accepted paper as stored in ``L_laid.json``."""

    y: int  # conference year
    t: str  # title
    ab: str  # abstract ("" when only the title is known)
    f: int  # fine topic id
    c: int  # area (coarse topic) id
    x: float  # 2D map coordinates
    y2: float
    tp: NotRequired[str]  # NeurIPS subject label (2023-2026 only)
    k: NotRequired[str]  # "poster" | "spotlight" | "oral"
    tr: NotRequired[str]  # "Main" | "D&B" | "Journal" | "Position"
    abs: NotRequired[str]  # abstract source: "neurips" | "arxiv" | ""
    au: NotRequired[list[list[str]]]  # [[name, institution], ...]


class DataDir:
    """Lazy accessor for the pipeline's intermediate files."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root).expanduser()
        if not self.root.is_dir():
            raise SystemExit(
                f"data directory not found: {self.root}\n"
                f"Pass --data-dir or set {DATA_ENV} (see paper/README.md, 'Data')."
            )

    def path(self, name: str) -> Path:
        return self.root / name

    def json(self, name: str) -> Any:
        return load_json(self.path(name))

    def papers(self) -> list[Paper]:
        return self.json("L_laid.json")

    def names(self) -> dict[str, dict[str, dict[str, str]]]:
        return self.json("names.json")

    def embeddings(self) -> Any:
        import numpy as np

        return np.load(self.path("emb.npy")).astype(np.float32)


def arxiv_key(p: Mapping[str, Any]) -> str:
    """Key used by ``arxiv.json`` and ``cites.json``."""
    return f"{p['y']}|{p['t']}"


def load_json(path: str | os.PathLike[str]) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str | os.PathLike[str], obj: Any, *, indent: int | None = 1, **kw: Any) -> Path:
    """Write ``obj`` as JSON (``indent=1``, the format of the committed results)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=indent, **kw)
    return path


def update_json(path: str | os.PathLike[str], new: Mapping[str, Any]) -> Path:
    """Merge ``new`` into the JSON object at ``path``; existing keys keep their position."""
    path = Path(path)
    obj = load_json(path) if path.exists() else {}
    obj.update(new)
    return write_json(path, obj)


def rounded(d: Mapping[str, Any], ndigits: int = 4) -> dict[str, float]:
    return {k: round(float(v), ndigits) for k, v in d.items()}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion ``k / n``."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def cohen_kappa(a: Iterable[str], b: Iterable[str]) -> float:
    """Cohen's kappa for two raters' categorical labels on the same items."""
    a, b = list(a), list(b)
    if len(a) != len(b) or not a:
        raise ValueError("need two equally long, non-empty label lists")
    n = len(a)
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def base_parser(description: str, *, data: bool = True) -> argparse.ArgumentParser:
    """Argument parser with the options every script shares."""
    ap = argparse.ArgumentParser(description=description)
    if data:
        ap.add_argument(
            "--data-dir",
            default=os.environ.get(DATA_ENV, str(PAPER_DIR / "data")),
            help=f"pipeline data directory (default: ${DATA_ENV} or paper/data)",
        )
    ap.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
        help="where result JSON files are read and written (default: paper/results)",
    )
    return ap
