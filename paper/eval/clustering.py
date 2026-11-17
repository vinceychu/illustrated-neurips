"""Agreement of the map's topics with NeurIPS subject labels (Section 5.1, Table 2).

Compares our fine topics / areas (UMAP k-means + Ward) with k-means on the raw
embeddings (three seeds), k-means on a TF-IDF/LSA projection and random assignment,
scored by NMI and ARI against the self-reported NeurIPS subject labels of 2023-2026,
plus a paired bootstrap of our gain over raw k-means (seed 0).

Updates ``results/paper_eval.json`` with:

* ``labels_v2``, ``cluster_v2``, ``bootstrap_ours_minus_kmeans`` -- labels normalised
  across the two formats (``A->B`` and ``A/B``); these are the numbers in Table 2.
* ``labelled``, ``n_full``, ``n_top``, ``cluster``, ``kmeans_raw_seeds`` -- the same
  comparison on raw, un-normalised labels (an earlier variant, kept for the record;
  not reported in the paper).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score as ari
from sklearn.metrics import homogeneity_completeness_v_measure as hcv
from sklearn.metrics import normalized_mutual_info_score as nmi

from .common import DataDir, Paper, base_parser, rounded, update_json

N_SEEDS = 3
N_BOOTSTRAP = 300
LSA_DIM = 256
Assignment = tuple[np.ndarray, np.ndarray]  # (fine, coarse) cluster id per paper


def kmeans(x: np.ndarray, k: int, seed: int) -> np.ndarray:
    return KMeans(k, n_init=4, random_state=seed).fit_predict(x)


def tfidf_lsa(papers: Sequence[Paper]) -> np.ndarray:
    """Unit-normalised 256-D LSA projection of TF-IDF over title + abstract."""
    docs = [p["t"] + " " + p["ab"] for p in papers]
    tfidf = TfidfVectorizer(min_df=3, max_df=0.3, stop_words="english", sublinear_tf=True)
    z = TruncatedSVD(LSA_DIM, random_state=0).fit_transform(tfidf.fit_transform(docs))
    return z / (np.linalg.norm(z, axis=1, keepdims=True) + 1e-9)


def assignments(papers: Sequence[Paper], emb: np.ndarray) -> dict[str, Assignment]:
    """(fine, coarse) assignment for ours, raw-embedding k-means (3 seeds) and TF-IDF/LSA k-means."""
    n_fine, n_coarse = len({p["f"] for p in papers}), len({p["c"] for p in papers})
    methods: dict[str, Assignment] = {"ours": (np.array([p["f"] for p in papers]), np.array([p["c"] for p in papers]))}
    for s in range(N_SEEDS):
        methods[f"kmeans_raw_s{s}"] = (kmeans(emb, n_fine, s), kmeans(emb, n_coarse, s))
    z = tfidf_lsa(papers)
    methods["tfidf_lsa"] = (kmeans(z, n_fine, 0), kmeans(z, n_coarse, 0))
    return methods


def normalise_label(label: str) -> list[str]:
    """Split a NeurIPS subject label written as ``A->B`` or ``A/B`` into its parts."""
    return [x.strip() for x in re.split(r"->|/", label) if x.strip()]


def legacy_scores(papers: Sequence[Paper], methods: dict[str, Assignment]) -> dict:
    """Scores against raw (un-normalised) labels. Not reported in the paper."""
    lab = [i for i, p in enumerate(papers) if p.get("tp")]
    full = [papers[i]["tp"] for i in lab]
    top = [papers[i]["tp"].split("->")[0].strip() for i in lab]

    def score(fine: np.ndarray, coarse: np.ndarray) -> dict[str, float]:
        f = fine[lab]
        h, c, v = hcv(full, f)
        r = {"nmi_full": nmi(full, f), "ari_full": ari(full, f), "hom": h, "comp": c, "v": v}
        r.update(nmi_top=nmi(top, coarse[lab]), ari_top=ari(top, coarse[lab]))
        return rounded(r)

    names = {
        "ours_umap_kmeans": "ours",
        "kmeans_raw_emb": "kmeans_raw_s0",
        "tfidf_lsa_kmeans": "tfidf_lsa",
        "random": "random",
    }
    seeds = []
    for s in range(N_SEEDS):
        fk, ck = methods[f"kmeans_raw_s{s}"]
        seeds.append([round(float(x), 4) for x in (nmi(full, fk[lab]), ari(full, fk[lab]), nmi(top, ck[lab]))])
    return {
        "labelled": len(lab),
        "n_full": len(set(full)),
        "n_top": len(set(top)),
        "cluster": {name: score(*methods[m]) for name, m in names.items()},
        "kmeans_raw_seeds": seeds,
    }


def scores(papers: Sequence[Paper], methods: dict[str, Assignment], rng: np.random.Generator) -> dict:
    """Table 2: scores against normalised labels and the paired bootstrap."""
    lab = np.array([i for i, p in enumerate(papers) if p.get("tp")])
    full = np.array(["->".join(normalise_label(papers[i]["tp"])) for i in lab])
    top = np.array([normalise_label(papers[i]["tp"])[0] for i in lab])

    labels = {
        "n": len(lab),
        "n_full": len(set(full)),
        "n_top": len(set(top)),
        "top": [[str(a), int(b)] for a, b in Counter(top).most_common(12)],
        "by_year": {str(k): v for k, v in sorted(Counter(int(papers[i]["y"]) for i in lab).items())},
    }

    table = {
        name: rounded(
            {
                "nmi_fine": nmi(full, f[lab]),
                "ari_fine": ari(full, f[lab]),
                "nmi_coarse": nmi(top, c[lab]),
                "ari_coarse": ari(top, c[lab]),
            }
        )
        for name, (f, c) in methods.items()
    }

    # Paired bootstrap over labelled papers: ours minus raw k-means (seed 0).
    fo, co = methods["ours"]
    fk, ck = methods["kmeans_raw_s0"]
    diffs: dict[str, list[float]] = {m: [] for m in ("nmi_fine", "ari_fine", "nmi_coarse", "ari_coarse")}
    for _ in range(N_BOOTSTRAP):
        ix = rng.integers(0, len(lab), len(lab))
        sub = lab[ix]
        diffs["nmi_fine"].append(nmi(full[ix], fo[sub]) - nmi(full[ix], fk[sub]))
        diffs["ari_fine"].append(ari(full[ix], fo[sub]) - ari(full[ix], fk[sub]))
        diffs["nmi_coarse"].append(nmi(top[ix], co[sub]) - nmi(top[ix], ck[sub]))
        diffs["ari_coarse"].append(ari(top[ix], co[sub]) - ari(top[ix], ck[sub]))
    boot = {
        m: {
            "mean": round(float(np.mean(v)), 4),
            "lo": round(float(np.percentile(v, 2.5)), 4),
            "hi": round(float(np.percentile(v, 97.5)), 4),
            "frac_pos": round(float(np.mean(np.array(v) > 0)), 3),
        }
        for m, v in diffs.items()
    }
    return {"labels_v2": labels, "cluster_v2": table, "bootstrap_ours_minus_kmeans": boot}


def run(data: DataDir) -> dict:
    papers = data.papers()
    emb = data.embeddings()
    if len(papers) != len(emb):
        raise SystemExit(f"L_laid.json has {len(papers)} papers but emb.npy has {len(emb)} rows")
    methods = assignments(papers, emb)
    # One generator, seed 0: first the random baseline, then the bootstrap resamples.
    rng = np.random.default_rng(0)
    n_fine, n_coarse = len({p["f"] for p in papers}), len({p["c"] for p in papers})
    methods["random"] = (rng.integers(0, n_fine, len(papers)), rng.integers(0, n_coarse, len(papers)))
    return {**legacy_scores(papers, methods), **scores(papers, methods, rng)}


def main(argv: list[str] | None = None) -> None:
    args = base_parser(__doc__.splitlines()[0]).parse_args(argv)
    out = run(DataDir(args.data_dir))
    path = update_json(args.results_dir / "paper_eval.json", out)
    for name, r in out["cluster_v2"].items():
        print(f"{name:16s} " + "  ".join(f"{k}={v:.4f}" for k, v in r.items()))
    print(f"updated {path}")


if __name__ == "__main__":
    main()
