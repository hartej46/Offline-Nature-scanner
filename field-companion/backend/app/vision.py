"""
Image handling for Field Companion.
Resize images for Gemma vision input.
"""

import base64
import io
import os
from typing import Optional

from PIL import Image


MAX_LONG_EDGE = 1024  # Plan says: long edge ≤ 1024 px


def resize_image(image_bytes: bytes, max_long_edge: int = MAX_LONG_EDGE) -> bytes:
    """
    Resize an image so the long edge is at most max_long_edge pixels.
    Returns the resized image as JPEG bytes.
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Convert RGBA to RGB if needed
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Only resize if needed
    width, height = img.size
    long_edge = max(width, height)

    if long_edge > max_long_edge:
        scale = max_long_edge / long_edge
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.LANCZOS)

    # Save as JPEG
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def image_to_base64(image_bytes: bytes, resize: bool = True) -> str:
    """Convert image bytes to base64 string, optionally resizing first."""
    if resize:
        image_bytes = resize_image(image_bytes)
    return base64.b64encode(image_bytes).decode("utf-8")


def load_and_encode_image(image_path: str, resize: bool = True) -> str:
    """Load an image file and return base64-encoded string."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    return image_to_base64(image_bytes, resize=resize)


def save_image(image_bytes: bytes, save_dir: str, filename: str) -> str:
    """Save image bytes to disk. Returns the full path."""
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, filename)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path
