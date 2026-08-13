"""Severity estimation (1-5) — heuristic, not a trained model.

Combines signals per PROJECT_SPEC.md §7.2:
  1. Category criticality baseline (CATEGORY_CRITICALITY, shared/frozen).
  2. Affected-area proxy: fraction of the image occupied by high-contrast
     detail, via a grayscale edge-density heuristic (PIL FIND_EDGES). This
     is a visual-clutter proxy.
  3. Classification confidence: blends the criticality+area estimate
     toward the neutral midpoint (3) when confidence is low, and leaves
     it unchanged when confidence is high — nudging toward the extremes
     only when the model is confident.
  4. Duplicate count: more independent reports of the same spot nudges
     the baseline severity higher (e.g. duplicate_count > 3 adds +1).

Formula:
  base = CATEGORY_CRITICALITY[category] (1-5)
  area_fraction = mean(FIND_EDGES(image_grayscale)) / 255.0
  area_adjustment = +1 if area_fraction > 0.35 else (-1 if area_fraction < 0.08 else 0)
  dup_adjustment = +1 if duplicate_count > 3 else 0
  raw_severity = clamp(base + area_adjustment + dup_adjustment, 1, 5)
  blended = confidence * raw_severity + (1 - confidence) * 3.0
  severity = clamp(round(blended), 1, 5)
"""

import numpy as np
from PIL import Image, ImageFilter

try:
    from app.scoring import CATEGORY_CRITICALITY
except ImportError:
    from ai.constants import CATEGORY_CRITICALITY

_LARGE_AREA_THRESHOLD = 0.35
_SMALL_AREA_THRESHOLD = 0.08


def _affected_area_fraction(image: Image.Image) -> float:
    gray = image.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    arr = np.asarray(edges, dtype=np.float32)
    return float(arr.mean() / 255.0)


def estimate_severity(
    image: Image.Image,
    category: str,
    confidence: float,
    duplicate_count: int = 1,
) -> int:
    """Estimates civic issue severity on a 1-5 scale."""
    base = CATEGORY_CRITICALITY.get(category, CATEGORY_CRITICALITY.get("other", 2))

    area_fraction = _affected_area_fraction(image)
    if area_fraction > _LARGE_AREA_THRESHOLD:
        area_adjustment = 1
    elif area_fraction < _SMALL_AREA_THRESHOLD:
        area_adjustment = -1
    else:
        area_adjustment = 0

    dup_adjustment = 1 if duplicate_count > 3 else 0

    raw = min(max(base + area_adjustment + dup_adjustment, 1), 5)
    blended = confidence * raw + (1 - confidence) * 3.0
    return min(max(round(blended), 1), 5)
