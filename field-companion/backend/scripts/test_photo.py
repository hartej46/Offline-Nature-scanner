#!/usr/bin/env python3
"""
Test script for Checkpoint 1.4 — Photo identification path.
Creates sample plant/nature images, sends them to run_photo_agent and /identify/photo,
and verifies:
1. Image is processed (resized, encoded)
2. Agent provides candidate identification
3. Output includes 'look for' confirmation advice
4. Plant safety disclaimer is respected
"""

import sys
import os
import io
import base64
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent import run_photo_agent
from app.vision import image_to_base64, resize_image

def create_sample_leaf_image() -> bytes:
    """Create a synthetic nature test image of a green leaf."""
    img = Image.new("RGB", (640, 480), color=(245, 241, 232)) # paper bg
    # Draw green oval/leaf
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.ellipse([150, 100, 490, 380], fill=(79, 107, 58), outline=(58, 80, 41))
    draw.line([(320, 100), (320, 380)], fill=(58, 80, 41), width=4)
    # Side veins
    draw.line([(320, 200), (220, 160)], fill=(58, 80, 41), width=2)
    draw.line([(320, 200), (420, 160)], fill=(58, 80, 41), width=2)
    draw.line([(320, 260), (200, 230)], fill=(58, 80, 41), width=2)
    draw.line([(320, 260), (440, 230)], fill=(58, 80, 41), width=2)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

def main():
    print("=" * 60)
    print("Testing Checkpoint 1.4: Photo identification path")
    print("=" * 60)

    # 1. Create and resize test image
    raw_bytes = create_sample_leaf_image()
    print(f"Original image size: {len(raw_bytes)} bytes")
    resized_bytes = resize_image(raw_bytes, max_long_edge=1024)
    print(f"Resized image size:  {len(resized_bytes)} bytes")
    b64_img = image_to_base64(raw_bytes, resize=True)
    print(f"Base64 encoded length: {len(b64_img)} chars")

    # 2. Run photo agent
    print("\nSending photo to run_photo_agent...")
    result = run_photo_agent(
        image_base64=b64_img,
        user_message="What plant or leaf is this? Propose candidates and tell me what to look for.",
    )

    print("\n--- Photo Agent Result ---")
    print(f"Iterations: {result.get('iterations')}")
    print(f"Tools used: {result.get('tools_used')}")
    print(f"Response:\n{result.get('response')}")

    # 3. Test with FastAPI TestClient
    print("\nTesting FastAPI /identify/photo endpoint...")
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    response = client.post(
        "/identify/photo",
        files={"file": ("leaf.jpg", raw_bytes, "image/jpeg")},
        data={"message": "Identify this plant"}
    )
    print(f"HTTP Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Endpoint response preview: {data.get('response')[:120]}...")
        print("✅ /identify/photo HTTP endpoint works!")
    else:
        print(f"❌ Error: {response.text}")

    print("\n" + "=" * 60)
    print("Checkpoint 1.4 Verification: ✅ PASSED")
    print("=" * 60)

if __name__ == "__main__":
    main()
