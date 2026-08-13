"""Tests for ai/dedup.py — 3-gate duplicate detection and similarity math."""

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from PIL import Image

from ai import dedup, embeddings
from ai.dedup import ReportCandidate

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def test_haversine_distance_zero():
    dist = dedup.haversine_distance_meters(28.4595, 77.0266, 28.4595, 77.0266)
    assert dist == 0.0


def test_haversine_distance_known():
    # 1 degree latitude difference is approx 111,139 meters
    dist = dedup.haversine_distance_meters(28.0, 77.0, 29.0, 77.0)
    assert 110_000 <= dist <= 112_000

    # Short distance (approx 50m)
    # 0.00045 degrees lat is ~50m
    dist_short = dedup.haversine_distance_meters(28.4595, 77.0266, 28.45995, 77.0266)
    assert 40 <= dist_short <= 60


def test_cosine_similarity():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    v4 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    v_zero = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    assert np.isclose(dedup.cosine_similarity(v1, v2), 1.0)
    assert np.isclose(dedup.cosine_similarity(v1, v3), 0.0)
    assert np.isclose(dedup.cosine_similarity(v1, v4), -1.0)
    assert np.isclose(dedup.cosine_similarity(v1, v_zero), 0.0)


def test_find_best_match():
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    candidates = [
        (1, np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        (2, np.array([0.9, 0.1, 0.0], dtype=np.float32) / np.linalg.norm([0.9, 0.1, 0.0])),
        (3, np.array([0.5, 0.5, 0.0], dtype=np.float32) / np.linalg.norm([0.5, 0.5, 0.0])),
    ]

    best_id, best_sim = dedup.find_best_match(query, candidates)
    assert best_id == 2
    assert best_sim > 0.9

    assert dedup.find_best_match(query, []) is None


def test_3gate_duplicate_all_pass():
    now = datetime.now(timezone.utc)
    base_vec = np.random.randn(512).astype(np.float32)
    base_vec /= np.linalg.norm(base_vec)

    # Controlled near-duplicate vector with cosine similarity ~0.95
    noise = np.random.randn(512).astype(np.float32)
    noise -= np.dot(base_vec, noise) * base_vec
    noise /= np.linalg.norm(noise)

    dup_vec = (0.95 * base_vec + np.sqrt(1 - 0.95**2) * noise).astype(np.float32)
    dup_vec /= np.linalg.norm(dup_vec)

    cand = ReportCandidate(
        id=101,
        category="pothole",
        latitude=28.4595,
        longitude=77.0266,
        created_at=now - timedelta(days=2),
        embedding=base_vec,
        is_duplicate_of=None,
    )

    # Query report: 40m away, 2 days later, same category, similar image
    result = dedup.find_duplicate_3gates(
        query_category="pothole",
        query_latitude=28.45985,  # ~39m north
        query_longitude=77.0266,
        query_created_at=now,
        query_embedding=dup_vec,
        candidates=[cand],
    )

    assert result is not None
    matched_id, similarity = result
    assert matched_id == 101
    assert similarity >= 0.86


def test_3gate_duplicate_with_real_sample_images():
    now = datetime.now(timezone.utc)
    pothole_path = SAMPLES_DIR / "pothole.jpg"
    pothole_dup_path = SAMPLES_DIR / "pothole_dup.jpg"
    garbage_path = SAMPLES_DIR / "garbage.jpg"

    if not pothole_path.exists() or not pothole_dup_path.exists():
        return

    with Image.open(pothole_path) as img1, Image.open(pothole_dup_path) as img2, Image.open(garbage_path) as img3:
        emb_pothole = embeddings.encode_image(img1.convert("RGB"))
        emb_pothole_dup = embeddings.encode_image(img2.convert("RGB"))
        emb_garbage = embeddings.encode_image(img3.convert("RGB"))

    # Near-duplicate pothole photo
    sim_dup = dedup.cosine_similarity(emb_pothole, emb_pothole_dup)
    assert sim_dup >= 0.86, f"Near duplicate similarity was {sim_dup}, expected >= 0.86"

    # Completely different image (pothole vs garbage)
    sim_diff = dedup.cosine_similarity(emb_pothole, emb_garbage)
    assert sim_diff < 0.86, f"Different images similarity was {sim_diff}, expected < 0.86"

    cand_pothole = ReportCandidate(
        id=1,
        category="pothole",
        latitude=28.4595,
        longitude=77.0266,
        created_at=now - timedelta(days=1),
        embedding=emb_pothole,
        is_duplicate_of=None,
    )

    # 1. Query near-duplicate: 30m away, same category -> duplicate matched!
    match = dedup.find_duplicate_3gates(
        query_category="pothole",
        query_latitude=28.4597,
        query_longitude=77.0266,
        query_created_at=now,
        query_embedding=emb_pothole_dup,
        candidates=[cand_pothole],
    )
    assert match is not None
    assert match[0] == 1
    assert match[1] >= 0.86

    # 2. Query different image: same spot -> rejected by visual gate
    match_diff = dedup.find_duplicate_3gates(
        query_category="pothole",
        query_latitude=28.4597,
        query_longitude=77.0266,
        query_created_at=now,
        query_embedding=emb_garbage,
        candidates=[cand_pothole],
    )
    assert match_diff is None


def test_3gate_gate1_geo_fail():
    now = datetime.now(timezone.utc)
    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)

    cand = ReportCandidate(
        id=102,
        category="pothole",
        latitude=28.4595,
        longitude=77.0266,
        created_at=now,
        embedding=vec,
        is_duplicate_of=None,
    )

    # Query report: 550m away (exceeds 100m radius)
    result = dedup.find_duplicate_3gates(
        query_category="pothole",
        query_latitude=28.4645,  # ~550m north
        query_longitude=77.0266,
        query_created_at=now,
        query_embedding=vec,
        candidates=[cand],
    )
    assert result is None


def test_3gate_gate1_category_mismatch():
    now = datetime.now(timezone.utc)
    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)

    cand = ReportCandidate(
        id=103,
        category="pothole",
        latitude=28.4595,
        longitude=77.0266,
        created_at=now,
        embedding=vec,
        is_duplicate_of=None,
    )

    # Query report: same spot, same image, but different category
    result = dedup.find_duplicate_3gates(
        query_category="garbage_dump",
        query_latitude=28.4595,
        query_longitude=77.0266,
        query_created_at=now,
        query_embedding=vec,
        candidates=[cand],
    )
    assert result is None


def test_3gate_gate1_non_canonical_ignored():
    now = datetime.now(timezone.utc)
    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)

    cand = ReportCandidate(
        id=104,
        category="pothole",
        latitude=28.4595,
        longitude=77.0266,
        created_at=now,
        embedding=vec,
        is_duplicate_of=50,  # Not canonical
    )

    result = dedup.find_duplicate_3gates(
        query_category="pothole",
        query_latitude=28.4595,
        query_longitude=77.0266,
        query_created_at=now,
        query_embedding=vec,
        candidates=[cand],
    )
    assert result is None


def test_3gate_gate2_time_fail():
    now = datetime.now(timezone.utc)
    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)

    cand = ReportCandidate(
        id=105,
        category="pothole",
        latitude=28.4595,
        longitude=77.0266,
        created_at=now - timedelta(days=45),  # 45 days ago (> 30 days)
        embedding=vec,
        is_duplicate_of=None,
    )

    result = dedup.find_duplicate_3gates(
        query_category="pothole",
        query_latitude=28.4595,
        query_longitude=77.0266,
        query_created_at=now,
        query_embedding=vec,
        candidates=[cand],
    )
    assert result is None


def test_3gate_gate3_visual_similarity_fail():
    now = datetime.now(timezone.utc)
    vec1 = np.random.randn(512).astype(np.float32)
    vec1 /= np.linalg.norm(vec1)

    # Orthogonal / random unrelated vector
    vec2 = np.random.randn(512).astype(np.float32)
    vec2 -= np.dot(vec1, vec2) * vec1
    vec2 /= np.linalg.norm(vec2)

    cand = ReportCandidate(
        id=106,
        category="pothole",
        latitude=28.4595,
        longitude=77.0266,
        created_at=now,
        embedding=vec1,
        is_duplicate_of=None,
    )

    # Same location and time, but completely different visual image
    result = dedup.find_duplicate_3gates(
        query_category="pothole",
        query_latitude=28.4595,
        query_longitude=77.0266,
        query_created_at=now,
        query_embedding=vec2,
        candidates=[cand],
    )
    assert result is None
