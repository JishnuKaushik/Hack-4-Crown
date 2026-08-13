"""Visual-similarity and 3-gate duplicate detection (PROJECT_SPEC.md §7.3).

Three gates, all must pass, evaluated in strict order:
  1. Geo: Haversine distance <= DUP_RADIUS_METERS (100 m) AND category matches AND canonical only
  2. Time: existing report created within DUP_TIME_WINDOW_DAYS (30 d)
  3. Visual: cosine similarity >= DUP_SIMILARITY_THRESHOLD (0.86)

Filter by geo+time first (cheap filter), then compute similarity only against that small candidate set.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import numpy as np

try:
    from app.scoring import (
        DUP_RADIUS_METERS,
        DUP_SIMILARITY_THRESHOLD,
        DUP_TIME_WINDOW_DAYS,
    )
except ImportError:
    from ai.constants import (
        DUP_RADIUS_METERS,
        DUP_SIMILARITY_THRESHOLD,
        DUP_TIME_WINDOW_DAYS,
    )


def haversine_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculates great-circle distance between two GPS points in meters."""
    earth_radius_meters = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return earth_radius_meters * c


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors. Assumes L2-normalized float32 vectors,
    with safe normalization fallback if unnormalized.
    """
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    if abs(norm_a - 1.0) < 1e-4 and abs(norm_b - 1.0) < 1e-4:
        return float(np.dot(a, b))
    return float(np.dot(a, b) / (norm_a * norm_b))


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


@dataclass
class ReportCandidate:
    id: int
    category: str
    latitude: float
    longitude: float
    created_at: datetime
    embedding: np.ndarray
    is_duplicate_of: int | None = None


def find_duplicate_3gates(
    query_category: str,
    query_latitude: float,
    query_longitude: float,
    query_created_at: datetime,
    query_embedding: np.ndarray,
    candidates: list[ReportCandidate],
    radius_meters: float = DUP_RADIUS_METERS,
    time_window_days: int = DUP_TIME_WINDOW_DAYS,
    similarity_threshold: float = DUP_SIMILARITY_THRESHOLD,
) -> tuple[int, float] | None:
    """Filters candidate reports through the 3 gates in order:
    1. Gate 1 (Geo + Category):
       - must be canonical (is_duplicate_of is None)
       - category must match
       - haversine distance <= radius_meters
    2. Gate 2 (Time):
       - created within time_window_days
    3. Gate 3 (Visual):
       - cosine similarity >= similarity_threshold (evaluated only on surviving candidates)

    Returns (best_matching_id, similarity) or None if no match passes all 3 gates.
    """
    if query_created_at.tzinfo is None:
        query_time = query_created_at.replace(tzinfo=timezone.utc)
    else:
        query_time = query_created_at.astimezone(timezone.utc)

    time_cutoff = query_time - timedelta(days=time_window_days)

    # Gate 1 & 2: Geo + Time + Category filtering (cheap filters first)
    filtered: list[tuple[int, np.ndarray]] = []
    for cand in candidates:
        if cand.is_duplicate_of is not None:
            continue
        if cand.category != query_category:
            continue

        # Check geo distance
        dist = haversine_distance_meters(
            query_latitude, query_longitude, cand.latitude, cand.longitude
        )
        if dist > radius_meters:
            continue

        # Check time window
        cand_time = (
            cand.created_at.replace(tzinfo=timezone.utc)
            if cand.created_at.tzinfo is None
            else cand.created_at.astimezone(timezone.utc)
        )
        if cand_time < time_cutoff or cand_time > query_time + timedelta(days=time_window_days):
            continue

        filtered.append((cand.id, cand.embedding))

    if not filtered:
        return None

    # Gate 3: Visual similarity check only on filtered subset
    match = find_best_match(query_embedding, filtered)
    if match is None:
        return None

    best_id, best_sim = match
    if best_sim < similarity_threshold:
        return None

    return best_id, best_sim
