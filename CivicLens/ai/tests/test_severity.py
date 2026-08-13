"""Tests for ai/severity.py."""

from PIL import Image, ImageDraw
from ai import severity
from ai.constants import CATEGORIES


def test_severity_range_all_categories():
    img = Image.new("RGB", (200, 200), color=(100, 100, 100))
    for cat in CATEGORIES:
        for conf in [0.0, 0.2, 0.5, 0.8, 1.0]:
            sev = severity.estimate_severity(img, cat, conf)
            assert isinstance(sev, int)
            assert 1 <= sev <= 5


def test_category_criticality_impact():
    img = Image.new("RGB", (200, 200), color=(100, 100, 100))
    # waterlogging has criticality 5, stray_animals has criticality 2
    sev_high = severity.estimate_severity(img, "waterlogging", 1.0)
    sev_low = severity.estimate_severity(img, "stray_animals", 1.0)
    assert sev_high > sev_low


def test_edge_density_area_heuristic():
    # Low edge density image (solid color)
    solid_img = Image.new("RGB", (200, 200), color=(100, 100, 100))
    low_area = severity._affected_area_fraction(solid_img)
    assert low_area < severity._SMALL_AREA_THRESHOLD

    # High edge density image (checkerboard / grid of lines)
    edge_img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(edge_img)
    for i in range(0, 200, 4):
        draw.line([(0, i), (200, i)], fill=(0, 0, 0), width=2)
        draw.line([(i, 0), (i, 200)], fill=(0, 0, 0), width=2)

    high_area = severity._affected_area_fraction(edge_img)
    assert high_area > low_area


def test_confidence_blending():
    img = Image.new("RGB", (200, 200), color=(100, 100, 100))
    # At confidence 0.0, score blends completely to 3
    sev_zero_conf = severity.estimate_severity(img, "waterlogging", 0.0)
    assert sev_zero_conf == 3
