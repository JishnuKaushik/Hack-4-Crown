"""CLIP model singleton + image embedding.

Loads the model once (module-level cache), not per call. Call warm_up()
at app startup so the (one-time, then locally cached) weight download and
model init happen before the first request rather than blocking it.
"""

import numpy as np
import open_clip
import torch
from PIL import Image

_MODEL_NAME = "ViT-B-32"
_PRETRAINED = "laion2b_s34b_b79k"

# Static, known ahead of time for ViT-B-32 — used by pipeline.py's failure
# fallback, which must not call embedding_dim() (that would load the model,
# defeating the point of a fallback for "the model failed to load").
EMBEDDING_DIM = 512

_model: torch.nn.Module | None = None
_preprocess = None
_tokenizer = None


def _get_model():
    global _model, _preprocess, _tokenizer
    if _model is None:
        model, _, preprocess = open_clip.create_model_and_transforms(
            _MODEL_NAME, pretrained=_PRETRAINED
        )
        model.eval()
        _model = model
        _preprocess = preprocess
        _tokenizer = open_clip.get_tokenizer(_MODEL_NAME)
    return _model, _preprocess, _tokenizer


def warm_up() -> None:
    """Force the model to load now instead of on the first request."""
    _get_model()


def embedding_dim() -> int:
    model, _, _ = _get_model()
    return int(model.visual.output_dim)


def encode_image(image: Image.Image) -> np.ndarray:
    """Returns a float32, L2-normalized embedding vector for one image."""
    model, preprocess, _ = _get_model()
    tensor = preprocess(image).unsqueeze(0)
    with torch.no_grad():
        features = model.encode_image(tensor)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.squeeze(0).to(torch.float32).cpu().numpy()


def encode_text(prompts: list[str]) -> np.ndarray:
    """Returns float32, L2-normalized embeddings, shape (len(prompts), dim)."""
    model, _, tokenizer = _get_model()
    tokens = tokenizer(prompts)
    with torch.no_grad():
        features = model.encode_text(tokens)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.to(torch.float32).cpu().numpy()
