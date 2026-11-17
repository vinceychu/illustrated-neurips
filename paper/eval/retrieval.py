"""Title-to-abstract search (Section 5.2, Table 3).

Samples 2,000 papers with abstracts, uses each title alone as the query and ranks all
papers with abstracts by similarity to their abstract only. Compares bge-small with and
without its retrieval instruction (the deployed setting), TF-IDF, and a z-score hybrid.

Updates ``results/paper_eval.json`` (``retrieval``, ``retrieval_n_queries``,
``retrieval_n_docs``). Needs ``sentence-transformers``; a GPU makes it fast.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .common import DataDir, Paper, base_parser, update_json

MODEL = "BAAI/bge-small-en-v1.5"
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
N_QUERIES = 2000


def query_sample(papers: Sequence[Paper], has_abstract: np.ndarray) -> np.ndarray:
    """The 2,000 query papers of the published run.

    The original script drew the clustering baseline's random assignment from the same
    seed-0 generator first, so we replay those two draws to get the identical sample.
    """
    rng = np.random.default_rng(0)
    rng.integers(0, len({p["f"] for p in papers}), len(papers))
    rng.integers(0, len({p["c"] for p in papers}), len(papers))
    return rng.choice(has_abstract, N_QUERIES, replace=False)


def rank_metrics(sim: np.ndarray, target: np.ndarray) -> dict[str, float]:
    """MRR, recall@k and median rank of each query's own paper (rank 1 = best)."""
    own = sim[np.arange(len(target)), target]
    ranks = (sim > own[:, None]).sum(axis=1) + 1
    return {
        k: round(float(v), 4)
        for k, v in {
            "mrr": (1 / ranks).mean(),
            "r1": (ranks <= 1).mean(),
            "r10": (ranks <= 10).mean(),
            "r100": (ranks <= 100).mean(),
            "median_rank": np.median(ranks),
        }.items()
    }


def zscore(s: np.ndarray, eps: float = 0.0) -> np.ndarray:
    return (s - s.mean(1, keepdims=True)) / (s.std(1, keepdims=True) + eps)


def run(data: DataDir) -> dict:
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    papers = data.papers()
    has = np.array([i for i, p in enumerate(papers) if p["ab"]])
    samp = query_sample(papers, has)
    pos = {int(i): k for k, i in enumerate(has)}
    target = np.array([pos[int(i)] for i in samp])
    abstracts = [papers[i]["ab"] for i in has]
    titles = [papers[i]["t"] for i in samp]

    model = SentenceTransformer(MODEL)
    enc = dict(batch_size=128, normalize_embeddings=True, show_progress_bar=False)
    doc_emb = model.encode(abstracts, **enc)
    q_plain = model.encode(titles, **enc)
    q_instr = model.encode([BGE_QUERY_INSTRUCTION + t for t in titles], **enc)

    tfidf = TfidfVectorizer(stop_words="english", sublinear_tf=True, min_df=2).fit(abstracts)
    s_tfidf = (normalize(tfidf.transform(titles)) @ normalize(tfidf.transform(abstracts)).T).toarray()
    s_instr = q_instr @ doc_emb.T

    return {
        "retrieval": {
            "bge_small_title_to_abstract": rank_metrics(q_plain @ doc_emb.T, target),
            "bge_small_title_to_abstract_instr": rank_metrics(s_instr, target),
            "tfidf_title_to_abstract": rank_metrics(s_tfidf, target),
            "hybrid_bge_tfidf": rank_metrics(zscore(s_instr) + zscore(s_tfidf, 1e-9), target),
        },
        "retrieval_n_queries": len(samp),
        "retrieval_n_docs": len(has),
    }


def main(argv: list[str] | None = None) -> None:
    args = base_parser(__doc__.splitlines()[0]).parse_args(argv)
    out = run(DataDir(args.data_dir))
    path = update_json(args.results_dir / "paper_eval.json", out)
    for name, r in out["retrieval"].items():
        print(f"{name:36s} " + "  ".join(f"{k}={v:.4f}" for k, v in r.items()))
    print(f"updated {path}")


if __name__ == "__main__":
    main()
