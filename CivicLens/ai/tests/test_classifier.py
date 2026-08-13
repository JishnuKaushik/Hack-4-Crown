"""Tests for ai/classifier.py."""

import numpy as np

from ai import classifier
from ai.constants import CATEGORIES


def test_prompts_match_categories():
    # Every prompt category must be in CATEGORIES
    for cat in classifier.PROMPTS:
        assert cat in CATEGORIES
    # All non-'other' categories should have a prompt
    for cat in CATEGORIES:
        if cat != "other":
            assert cat in classifier.PROMPTS


def test_classify_returns_valid_category_and_confidence():
    text_features = classifier._get_text_features()
    # Use first category's text vector as a surrogate image vector
    dummy_embedding = text_features[0].copy()
    dummy_embedding /= np.linalg.norm(dummy_embedding)

    category, confidence = classifier.classify(dummy_embedding)
    assert category in CATEGORIES
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    # First prompt should match highest
    assert category == classifier._CATEGORY_ORDER[0]
    assert confidence >= classifier._CONFIDENCE_FLOOR


def test_classify_confidence_floor():
    # Create an orthogonal or uniform vector where no prompt has high confidence
    # Create zero vector or noise vector
    noise = np.ones(512, dtype=np.float32)
    noise /= np.linalg.norm(noise)

    # When all logits are identical, softmax is 1/N = 1/10 = 0.10 < 0.25
    # Let's craft an embedding where top probability is < 0.25
    category, confidence = classifier.classify(noise)
    if confidence < classifier._CONFIDENCE_FLOOR:
        assert category == "other"
