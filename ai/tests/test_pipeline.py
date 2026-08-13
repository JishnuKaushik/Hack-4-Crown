"""Tests for ai/pipeline.py — end-to-end image analysis and safe fallback."""

from pathlib import Path
import numpy as np

from ai.pipeline import analyze_image, AnalysisResult
from ai.constants import CATEGORIES

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def test_analyze_image_pothole():
    pothole_path = SAMPLES_DIR / "pothole.jpg"
    assert pothole_path.exists(), "Sample pothole.jpg must exist"

    result = analyze_image(str(pothole_path), 28.4595, 77.0266)

    assert isinstance(result, AnalysisResult)
    assert result.category == "pothole"
    assert result.confidence >= 0.25
    assert 1 <= result.severity <= 5
    assert isinstance(result.embedding, np.ndarray)
    assert result.embedding.shape == (512,)
    assert result.embedding.dtype == np.float32
    assert np.isclose(np.linalg.norm(result.embedding), 1.0, atol=1e-3)


def test_analyze_image_garbage():
    garbage_path = SAMPLES_DIR / "garbage.jpg"
    assert garbage_path.exists(), "Sample garbage.jpg must exist"

    result = analyze_image(str(garbage_path), 28.4595, 77.0266)

    assert isinstance(result, AnalysisResult)
    assert result.category == "garbage_dump"
    assert result.confidence >= 0.25
    assert 1 <= result.severity <= 5
    assert result.embedding.shape == (512,)


def test_analyze_image_waterlogging():
    waterlog_path = SAMPLES_DIR / "waterlogging.jpg"
    assert waterlog_path.exists(), "Sample waterlogging.jpg must exist"

    result = analyze_image(str(waterlog_path), 28.4595, 77.0266)

    assert isinstance(result, AnalysisResult)
    assert result.category == "waterlogging"
    assert result.confidence >= 0.25
    assert 1 <= result.severity <= 5
    assert result.embedding.shape == (512,)


def test_analyze_image_corrupt_file_fallback():
    corrupt_path = SAMPLES_DIR / "corrupt.jpg"
    assert corrupt_path.exists(), "Sample corrupt.jpg must exist"

    # Must NEVER raise, returns safe fallback
    result = analyze_image(str(corrupt_path), 28.4595, 77.0266)

    assert isinstance(result, AnalysisResult)
    assert result.category == "other"
    assert result.confidence == 0.0
    assert result.severity == 3
    assert result.embedding.shape == (512,)
    assert np.all(result.embedding == 0.0)


def test_analyze_image_missing_file_fallback():
    missing_path = SAMPLES_DIR / "does_not_exist_12345.jpg"

    # Must NEVER raise, returns safe fallback
    result = analyze_image(str(missing_path), 28.4595, 77.0266)

    assert isinstance(result, AnalysisResult)
    assert result.category == "other"
    assert result.confidence == 0.0
    assert result.severity == 3
    assert result.embedding.shape == (512,)
    assert np.all(result.embedding == 0.0)


def test_analyze_image_never_raises_on_invalid_inputs():
    # Pass invalid inputs (None, wrong types)
    result = analyze_image(None, 0.0, 0.0)
    assert isinstance(result, AnalysisResult)
    assert result.category == "other"
    assert result.confidence == 0.0
    assert result.severity == 3
