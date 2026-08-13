import math
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai import dedup as ai_dedup
from app.geo import haversine_distance_meters
from app.models import Report, ReportEmbedding
from app.scoring import DUP_RADIUS_METERS, DUP_SIMILARITY_THRESHOLD, DUP_TIME_WINDOW_DAYS

_METERS_PER_DEGREE_LAT = 111_320


def find_duplicate_canonical(
    db: Session, *, category: str, latitude: float, longitude: float, embedding: np.ndarray
) -> Report | None:
    """Three gates, all required (PROJECT_SPEC.md §7.3): geo <= DUP_RADIUS_METERS,
    time within DUP_TIME_WINDOW_DAYS, visual cosine similarity >=
    DUP_SIMILARITY_THRESHOLD. Category must also match. Only matches against
    existing canonical reports (is_duplicate_of IS NULL).

    Cheap SQL (bounding box + time) filters first; exact haversine + cosine
    similarity only run against that small candidate set.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=DUP_TIME_WINDOW_DAYS)

    lat_delta = DUP_RADIUS_METERS / _METERS_PER_DEGREE_LAT
    lng_denominator = _METERS_PER_DEGREE_LAT * math.cos(math.radians(latitude))
    lng_delta = DUP_RADIUS_METERS / abs(lng_denominator) if lng_denominator else 180

    stmt = (
        select(Report, ReportEmbedding)
        .join(ReportEmbedding, ReportEmbedding.report_id == Report.id)
        .where(
            Report.category == category,
            Report.is_duplicate_of.is_(None),
            Report.created_at >= cutoff,
            Report.latitude.between(latitude - lat_delta, latitude + lat_delta),
            Report.longitude.between(longitude - lng_delta, longitude + lng_delta),
        )
    )
    rows = db.execute(stmt).all()

    geo_filtered: list[tuple[Report, np.ndarray]] = []
    for report, report_embedding in rows:
        distance = haversine_distance_meters(latitude, longitude, report.latitude, report.longitude)
        if distance <= DUP_RADIUS_METERS:
            vec = np.frombuffer(report_embedding.vector, dtype=np.float32)
            geo_filtered.append((report, vec))

    if not geo_filtered:
        return None

    candidates = [(report.id, vec) for report, vec in geo_filtered]
    match = ai_dedup.find_best_match(embedding, candidates)
    if match is None:
        return None

    best_id, best_similarity = match
    if best_similarity < DUP_SIMILARITY_THRESHOLD:
        return None

    return next(report for report, _ in geo_filtered if report.id == best_id)
