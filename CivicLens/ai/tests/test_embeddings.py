"""Tests for ai/embeddings.py."""

import numpy as np
from PIL import Image

from ai import embeddings


def test_embedding_constants():
    assert embeddings.EMBEDDING_DIM == 512
    assert embeddings.embedding_dim() == 512


def test_warm_up():
    embeddings.warm_up()
    assert embeddings._model is not None


def test_encode_image():
    # Create a small RGB test image
    img = Image.new("RGB", (224, 224), color=(128, 64, 32))
    emb = embeddings.encode_image(img)

    assert isinstance(emb, np.ndarray)
    assert emb.dtype == np.float32
    assert emb.shape == (512,)
    # Verify L2 normalization
    norm = np.linalg.norm(emb)
    assert np.isclose(norm, 1.0, atol=1e-3)


def test_encode_text():
    prompts = ["a photo of a pothole", "a photo of garbage"]
    embs = embeddings.encode_text(prompts)

    assert isinstance(embs, np.ndarray)
    assert embs.dtype == np.float32
    assert embs.shape == (2, 512)

    for i in range(len(prompts)):
        norm = np.linalg.norm(embs[i])
        assert np.isclose(norm, 1.0, atol=1e-3)
