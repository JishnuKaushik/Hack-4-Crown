"""Visual-similarity gate for duplicate detection (PROJECT_SPEC.md §7.3).

Pure math only — no DB access. The geo+time SQL pre-filter that narrows
candidates down to a small set happens in the backend (app/dedup.py);
this module just scores that already-small candidate set.
"""

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Both vectors are assumed already L2-normalized (PROJECT_SPEC.md §5),
    so cosine similarity reduces to a plain dot product.
    """
    return float(np.dot(a, b))


def find_best_match(
    query: np.ndarray, candidates: list[tuple[int, np.ndarray]]
) -> tuple[int, float] | None:
    """candidates: (report_id, embedding) pairs. Returns the best-matching
    (report_id, similarity), or None if candidates is empty.
    """
    if not candidates:
        return None
    best_id, best_sim = candidates[0][0], -1.0
    for report_id, vec in candidates:
        sim = cosine_similarity(query, vec)
        if sim > best_sim:
            best_id, best_sim = report_id, sim
    return best_id, best_sim
