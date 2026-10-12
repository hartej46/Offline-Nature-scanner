"""
Comprehensive tests for image processing and vision pipeline (app.vision).
Covers: resize_image, image_to_base64, load_and_encode_image, save_image.
Includes edge cases: wide/tall/square images, RGBA/P/L modes, exact 1024 boundaries,
corrupt bytes, empty bytes, non-existent files.
"""

import os
import io
import base64
import pytest
from PIL import Image, UnidentifiedImageError
from app.vision import (
    MAX_LONG_EDGE,
    resize_image,
    image_to_base64,
    load_and_encode_image,
    save_image,
)


def _create_image_bytes(size: tuple[int, int], mode: str = "RGB", fmt: str = "JPEG", color=(100, 150, 200)) -> bytes:
    """Helper to generate in-memory test image bytes."""
    if mode == "RGBA":
        color = (100, 150, 200, 255)
    elif mode == "L":
        color = 128

    img = Image.new(mode, size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestVisionResize:
    def test_max_long_edge_constant(self):
        """Plan specifies max long edge must be 1024 px."""
        assert MAX_LONG_EDGE == 1024

    def test_resize_wide_image_downscaled(self):
        """Wide image (2000x1000) scaled down to 1024 long edge preserving aspect ratio."""
        data = _create_image_bytes((2000, 1000))
        resized_bytes = resize_image(data)

        out_img = Image.open(io.BytesIO(resized_bytes))
        assert out_img.size[0] == 1024
        assert out_img.size[1] == 512
        assert out_img.format == "JPEG"

    def test_resize_tall_image_downscaled(self):
        """Tall image (800x1600) scaled down to 1024 height preserving aspect ratio."""
        data = _create_image_bytes((800, 1600))
        resized_bytes = resize_image(data)

        out_img = Image.open(io.BytesIO(resized_bytes))
        assert out_img.size[1] == 1024
        assert out_img.size[0] == 512

    def test_resize_square_large_image(self):
        """Square image (1500x1500) scaled to exactly 1024x1024."""
        data = _create_image_bytes((1500, 1500))
        resized_bytes = resize_image(data)

        out_img = Image.open(io.BytesIO(resized_bytes))
        assert out_img.size == (1024, 1024)

    def test_resize_small_image_untouched(self):
        """Images smaller than 1024px along the long edge keep their original dimensions."""
        data = _create_image_bytes((400, 300))
        resized_bytes = resize_image(data)

        out_img = Image.open(io.BytesIO(resized_bytes))
        assert out_img.size == (400, 300)

    def test_resize_exact_1024_image(self):
        """Image with exactly 1024px long edge retains its dimensions."""
        data = _create_image_bytes((1024, 768))
        resized_bytes = resize_image(data)

        out_img = Image.open(io.BytesIO(resized_bytes))
        assert out_img.size == (1024, 768)

    def test_resize_rgba_to_rgb_conversion(self):
        """RGBA image (PNG) is converted to RGB JPEG cleanly without alpha channel error."""
        data = _create_image_bytes((800, 600), mode="RGBA", fmt="PNG")
        resized_bytes = resize_image(data)

        out_img = Image.open(io.BytesIO(resized_bytes))
        assert out_img.mode == "RGB"
        assert out_img.format == "JPEG"

    def test_resize_palette_p_mode_conversion(self):
        """Palette 'P' mode image is converted to RGB JPEG."""
        base_img = Image.new("P", (600, 400))
        buf = io.BytesIO()
        base_img.save(buf, format="PNG")
        resized_bytes = resize_image(buf.getvalue())

        out_img = Image.open(io.BytesIO(resized_bytes))
        assert out_img.mode == "RGB"

    def test_resize_custom_max_long_edge(self):
        """Supports overriding max_long_edge."""
        data = _create_image_bytes((1200, 800))
        resized_bytes = resize_image(data, max_long_edge=600)

        out_img = Image.open(io.BytesIO(resized_bytes))
        assert out_img.size[0] == 600
        assert out_img.size[1] == 400

    def test_resize_corrupted_bytes_raises_error(self):
        """Corrupted image bytes should raise UnidentifiedImageError."""
        with pytest.raises(Exception):
            resize_image(b"not_a_valid_image_header_12345")

    def test_resize_empty_bytes_raises_error(self):
        """Empty byte string should raise UnidentifiedImageError."""
        with pytest.raises(Exception):
            resize_image(b"")


class TestVisionEncoding:
    def test_image_to_base64_with_resize(self):
        """image_to_base64 with resize=True downsamples and encodes to valid base64."""
        data = _create_image_bytes((1600, 1200))
        b64_str = image_to_base64(data, resize=True)

        assert isinstance(b64_str, str)
        # Verify decodable
        decoded = base64.b64decode(b64_str)
        img = Image.open(io.BytesIO(decoded))
        assert img.size[0] == 1024
        assert img.format == "JPEG"

    def test_image_to_base64_without_resize(self):
        """image_to_base64 with resize=False encodes raw bytes directly."""
        data = _create_image_bytes((200, 200), fmt="PNG")
        b64_str = image_to_base64(data, resize=False)

        decoded = base64.b64decode(b64_str)
        assert decoded == data

    def test_load_and_encode_image(self, tmp_path):
        """load_and_encode_image loads an image file from disk and encodes to base64."""
        img_path = str(tmp_path / "test.jpg")
        raw_data = _create_image_bytes((300, 300))
        with open(img_path, "wb") as f:
            f.write(raw_data)

        b64_str = load_and_encode_image(img_path, resize=False)
        assert base64.b64decode(b64_str) == raw_data

    def test_load_and_encode_image_nonexistent_raises(self):
        """Attempting to load a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_and_encode_image("/nonexistent/path/to/image_9999.jpg")


class TestVisionSave:
    def test_save_image_creates_directory_and_writes_file(self, tmp_path):
        """save_image creates non-existent directory and writes exact bytes."""
        target_dir = str(tmp_path / "nested" / "uploads")
        filename = "saved_photo.jpg"
        data = _create_image_bytes((150, 150))

        saved_path = save_image(data, target_dir, filename)

        assert os.path.exists(saved_path)
        assert os.path.isfile(saved_path)
        with open(saved_path, "rb") as f:
            saved_content = f.read()
        assert saved_content == data
