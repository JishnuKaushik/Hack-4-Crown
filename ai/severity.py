"""Severity estimation (1-5) — heuristic, not a trained model.

Combines three signals per PROJECT_SPEC.md §7.2:
  1. Category criticality baseline (CATEGORY_CRITICALITY, shared/frozen).
  2. Affected-area proxy: fraction of the image occupied by high-contrast
     detail, via a grayscale edge-density heuristic (PIL FIND_EDGES). This
     is a rough visual-clutter proxy, not real segmentation — a genuinely
     large, uniform flood or garbage pile can score low on this signal.
  3. Classification confidence: blends the criticality+area estimate
     toward the neutral midpoint (3) when confidence is low, and leaves
     it unchanged when confidence is high — i.e. "nudges toward the
     extremes" only when the model is actually sure.

Signal 4 from the spec ("duplicate count") is intentionally NOT included
here: analyze_image()'s signature (image_path, lat, lng) has no report-
count input, and per the core flow in PROJECT_SPEC.md §1, severity is
computed *before* the dedup check runs. report_count already feeds
priority_score directly via W_REPORTS (scoring.py) — that's where repeat
reports raise a report's ranking today. If per-report severity should
also rise on merge, that's a P3 dedup-merge decision, not part of this
function.

All thresholds below (0.35 / 0.08 area cutoffs) are heuristic constants,
not derived from data — documented here rather than asserted as tuned.
"""

import numpy as np
from PIL import Image, ImageFilter

from app.scoring import CATEGORY_CRITICALITY

_LARGE_AREA_THRESHOLD = 0.35
_SMALL_AREA_THRESHOLD = 0.08


def _affected_area_fraction(image: Image.Image) -> float:
    gray = image.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    arr = np.asarray(edges, dtype=np.float32)
    return float(arr.mean() / 255.0)


def estimate_severity(image: Image.Image, category: str, confidence: float) -> int:
    base = CATEGORY_CRITICALITY.get(category, CATEGORY_CRITICALITY["other"])

    area_fraction = _affected_area_fraction(image)
    if area_fraction > _LARGE_AREA_THRESHOLD:
        area_adjustment = 1
    elif area_fraction < _SMALL_AREA_THRESHOLD:
        area_adjustment = -1
    else:
        area_adjustment = 0

    raw = min(max(base + area_adjustment, 1), 5)
    blended = confidence * raw + (1 - confidence) * 3.0
    return min(max(round(blended), 1), 5)
