"""Shared constants and priority-score formula — frozen per PROJECT_SPEC.md §4.

This is the single source of truth. ai/ mirrors these values; do not
duplicate the formula anywhere else.
"""

CATEGORIES = [
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

STATUSES = ["reported", "acknowledged", "in_progress", "resolved", "rejected"]

DUP_SIMILARITY_THRESHOLD = 0.86
DUP_RADIUS_METERS = 100
DUP_TIME_WINDOW_DAYS = 30

W_SEVERITY = 0.40
W_CRITICALITY = 0.25
W_REPORTS = 0.20
W_AGE = 0.15

assert abs(W_SEVERITY + W_CRITICALITY + W_REPORTS + W_AGE - 1.0) < 1e-9


def compute_priority_score(
    *,
    severity: int,
    category: str,
    report_count: int,
    age_days: float,
) -> float:
    """priority = 100 * (Wsev*(sev/5) + Wcrit*(crit/5) + Wrep*min(rc/10,1) + Wage*min(age/14,1))

    Range 0-100, rounded to 1 decimal. See PROJECT_SPEC.md §4.
    """
    criticality = CATEGORY_CRITICALITY.get(category, CATEGORY_CRITICALITY["other"])
    score = 100 * (
        W_SEVERITY * (severity / 5)
        + W_CRITICALITY * (criticality / 5)
        + W_REPORTS * min(report_count / 10, 1.0)
        + W_AGE * min(age_days / 14, 1.0)
    )
    return round(score, 1)
