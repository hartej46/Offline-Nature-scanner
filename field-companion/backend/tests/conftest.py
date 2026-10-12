"""
Shared pytest fixtures for Field Companion backend tests.
"""

import os
import io
import sys
import pytest
import numpy as np
import soundfile as sf
from PIL import Image
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database is initialized before any tests run."""
    init_db()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def sample_image_bytes():
    """Generate a valid test image (RGB, 1200x800) as JPEG bytes."""
    img = Image.new("RGB", (1200, 800), color=(79, 107, 58))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def small_image_bytes():
    """Generate a small test image (100x100) as PNG bytes."""
    img = Image.new("RGBA", (100, 100), color=(245, 241, 232, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_audio_wav(tmp_path):
    """Generate a short 1-second sine wave audio file (4000 Hz) as WAV."""
    path = str(tmp_path / "test_tone.wav")
    sr = 22050
    t = np.linspace(0, 1.0, sr, endpoint=False)
    # Sine wave tone
    tone = 0.5 * np.sin(2 * np.pi * 3800 * t)
    sf.write(path, tone, sr, subtype="PCM_16")
    return path


@pytest.fixture
def silent_audio_wav(tmp_path):
    """Generate a silent audio file."""
    path = str(tmp_path / "silent.wav")
    sr = 22050
    silence = np.zeros(int(sr * 1.0), dtype=np.float32)
    sf.write(path, silence, sr, subtype="PCM_16")
    return path
