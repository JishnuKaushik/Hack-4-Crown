"""ai/constants.py — Shared constants mirrored from PROJECT_SPEC.md §4.

Frozen schema and threshold values for classification, severity, and duplicate detection.
"""

CATEGORIES: list[str] = [
    "pothole",
    "garbage_dump",
    "broken_streetlight",
    "waterlogging",
    "damaged_road",
    "sewage_overflow",
    "broken_footpath",
    "fallen_tree",
    "stray_animals",
    "illegal_dumping",
    "other",
]

# How dangerous the category is regardless of visual severity (1-5)
CATEGORY_CRITICALITY: dict[str, int] = {
    "sewage_overflow": 5,
    "waterlogging": 5,
    "fallen_tree": 5,
    "pothole": 4,
    "damaged_road": 4,
    "broken_streetlight": 4,
    "garbage_dump": 3,
    "illegal_dumping": 3,
    "broken_footpath": 3,
    "stray_animals": 2,
    "other": 2,
}

STATUSES: list[str] = ["reported", "acknowledged", "in_progress", "resolved", "rejected"]

# Duplicate detection thresholds (PROJECT_SPEC.md §4)
DUP_SIMILARITY_THRESHOLD: float = 0.86  # cosine similarity on CLIP embeddings
DUP_RADIUS_METERS: float = 100.0        # Haversine distance in meters
DUP_TIME_WINDOW_DAYS: int = 30          # Recency window in days

# Priority weights (must sum to 1.0)
W_SEVERITY: float = 0.40
W_CRITICALITY: float = 0.25
W_REPORTS: float = 0.20
W_AGE: float = 0.15
