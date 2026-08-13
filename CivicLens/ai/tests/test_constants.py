"""Tests for ai/constants.py and category definitions."""

from ai.constants import (
    CATEGORIES,
    CATEGORY_CRITICALITY,
    STATUSES,
    DUP_RADIUS_METERS,
    DUP_SIMILARITY_THRESHOLD,
    DUP_TIME_WINDOW_DAYS,
)


def test_categories_defined():
    assert "pothole" in CATEGORIES
    assert "garbage_dump" in CATEGORIES
    assert "broken_streetlight" in CATEGORIES
    assert "waterlogging" in CATEGORIES
    assert "other" in CATEGORIES
    assert len(CATEGORIES) == 11


def test_category_criticality():
    for cat in CATEGORIES:
        crit = CATEGORY_CRITICALITY.get(cat)
        assert crit is not None
        assert 1 <= crit <= 5


def test_statuses():
    assert STATUSES == ["reported", "acknowledged", "in_progress", "resolved", "rejected"]


def test_dedup_thresholds():
    assert DUP_SIMILARITY_THRESHOLD == 0.86
    assert DUP_RADIUS_METERS == 100.0
    assert DUP_TIME_WINDOW_DAYS == 30
