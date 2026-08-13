"""Zero-shot CLIP classification — no training, compares an image embedding
against one natural-language prompt per category.
"""

import numpy as np

from ai import embeddings
try:
    from app.scoring import CATEGORIES
except ImportError:
    from ai.constants import CATEGORIES

PROMPTS: dict[str, str] = {
    "pothole": "a photo of a pothole in a road",
    "garbage_dump": "a photo of a pile of garbage on the street",
    "broken_streetlight": "a photo of a damaged or broken street light",
    "waterlogging": "a photo of a flooded waterlogged street",
    "damaged_road": "a photo of a damaged or cracked road surface",
    "sewage_overflow": "a photo of sewage overflowing onto a street",
    "broken_footpath": "a photo of a broken or damaged footpath",
    "fallen_tree": "a photo of a fallen tree blocking a road or path",
    "stray_animals": "a photo of stray animals on a street",
    "illegal_dumping": "a photo of illegally dumped waste or debris",
}

_CATEGORY_ORDER = list(PROMPTS.keys())
_CONFIDENCE_FLOOR = 0.25

# CLIP's trained logit_scale.exp() is ~100; using fixed scale for pre-softmax
# logits is the standard zero-shot CLIP classification recipe.
_LOGIT_SCALE = 100.0

_text_features: np.ndarray | None = None


def _get_text_features() -> np.ndarray:
    global _text_features
    if _text_features is None:
        _text_features = embeddings.encode_text([PROMPTS[c] for c in _CATEGORY_ORDER])
    return _text_features


def classify(image_embedding: np.ndarray) -> tuple[str, float]:
    """Returns (category, confidence). Category falls back to "other" when
    the top softmax probability is below _CONFIDENCE_FLOOR (0.25); the actual
    computed confidence is returned.
    """
    text_features = _get_text_features()
    logits = _LOGIT_SCALE * (text_features @ image_embedding)
    probs = np.exp(logits - logits.max())
    probs /= probs.sum()

    best_idx = int(np.argmax(probs))
    confidence = float(probs[best_idx])
    category = _CATEGORY_ORDER[best_idx] if confidence >= _CONFIDENCE_FLOOR else "other"

    return category, confidence
