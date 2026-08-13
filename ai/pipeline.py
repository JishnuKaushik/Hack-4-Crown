"""ai/pipeline.py — the ONLY entry point the backend calls (PROJECT_SPEC.md §7).

analyze_image() must never raise. Any internal failure (model not loaded,
corrupt image, out of memory, ...) is caught here and mapped to the safe
fallback so a report submission never fails because of the AI layer
(CLAUDE.md §4 degradation rule).

Fallback category is "other" — the literal member of the frozen CATEGORIES
list (PROJECT_SPEC.md §4/§7) reserved for "not confidently classified".
CLAUDE.md §4 describes the same fallback behavior using the word
"unclassified", which is not itself a member of CATEGORIES; PROJECT_SPEC
is the authoritative contract for schema/enum values (per CLAUDE.md's own
"PROJECT_SPEC.md is the source of truth for architecture, schema, and API
contracts" preamble), so "other" is what's actually returned/stored.
"""

import logging
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, UnidentifiedImageError

from ai import classifier, embeddings, severity as severity_module
from app.config import settings

logger = logging.getLogger(__name__)

_FALLBACK_CATEGORY = "other"
_FALLBACK_CONFIDENCE = 0.0
_FALLBACK_SEVERITY = 3


@dataclass
class AnalysisResult:
    category: str
    confidence: float
    severity: int
    embedding: np.ndarray = field(repr=False)


def _fallback() -> AnalysisResult:
    return AnalysisResult(
        category=_FALLBACK_CATEGORY,
        confidence=_FALLBACK_CONFIDENCE,
        severity=_FALLBACK_SEVERITY,
        embedding=np.zeros(embeddings.EMBEDDING_DIM, dtype=np.float32),
    )


def analyze_image(image_path: str, lat: float, lng: float) -> AnalysisResult:
    if not settings.ai_enabled:
        return _fallback()
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            image_embedding = embeddings.encode_image(img)
            category, confidence = classifier.classify(image_embedding)
            sev = severity_module.estimate_severity(img, category, confidence)
        return AnalysisResult(
            category=category,
            confidence=confidence,
            severity=sev,
            embedding=image_embedding.astype(np.float32),
        )
    except (UnidentifiedImageError, OSError, ValueError, RuntimeError) as exc:
        logger.warning("analyze_image failed for %s, using fallback: %s", image_path, exc)
        return _fallback()
