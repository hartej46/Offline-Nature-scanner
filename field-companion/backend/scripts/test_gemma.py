#!/usr/bin/env python3
"""
Checkpoint 1.1 — Test script for Gemma 4 E4B via Ollama's OpenAI-compatible API.
Tests text completion, image description, and records performance metrics.
"""

import os
import time
import json
import base64
import subprocess
from openai import OpenAI

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:e4b")

client = OpenAI(base_url=LLM_BASE_URL, api_key="unused")  # Ollama ignores API key


def test_text():
    """Test 1: Basic text completion."""
    print("=" * 60)
    print("TEST 1: Text completion")
    print("=" * 60)

    start = time.time()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": "What is a robin? Answer in 2 sentences."}],
        max_tokens=100,
    )
    elapsed = time.time() - start

    reply = response.choices[0].message.content
    usage = response.usage

    print(f"Reply: {reply}")
    print(f"Prompt tokens: {usage.prompt_tokens}")
    print(f"Completion tokens: {usage.completion_tokens}")
    print(f"Total tokens: {usage.total_tokens}")
    print(f"Time: {elapsed:.2f}s")

    if usage.completion_tokens and elapsed > 0:
        tps = usage.completion_tokens / elapsed
        print(f"Tokens/sec: {tps:.1f}")
    else:
        tps = None

    print("✅ Text completion works!\n")
    return {
        "test": "text",
        "tokens_per_sec": round(tps, 1) if tps else None,
        "elapsed_sec": round(elapsed, 2),
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
    }


def test_image():
    """Test 2: Image description (if supported)."""
    print("=" * 60)
    print("TEST 2: Image description")
    print("=" * 60)

    # Create a simple test image using Python (a green square — representing a plant)
    try:
        from PIL import Image
        img = Image.new("RGB", (256, 256), color=(34, 139, 34))  # Forest green
        img_path = "/tmp/test_plant.png"
        img.save(img_path)
    except ImportError:
        # Fallback: create a minimal PNG without PIL
        print("PIL not available, creating minimal test image...")
        import struct
        import zlib

        def create_minimal_png(path, width=4, height=4):
            """Create a tiny valid PNG file."""

            def chunk(chunk_type, data):
                c = chunk_type + data
                crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
                return struct.pack(">I", len(data)) + c + crc

            header = b"\x89PNG\r\n\x1a\n"
            ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            # Green pixels
            raw = b""
            for _ in range(height):
                raw += b"\x00"  # filter byte
                for _ in range(width):
                    raw += b"\x22\x8b\x22"  # forest green RGB
            idat = chunk(b"IDAT", zlib.compress(raw))
            iend = chunk(b"IEND", b"")
            with open(path, "wb") as f:
                f.write(header + ihdr + idat + iend)

        img_path = "/tmp/test_plant.png"
        create_minimal_png(img_path)

    # Encode image as base64
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    start = time.time()
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image briefly."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                        },
                    ],
                }
            ],
            max_tokens=100,
        )
        elapsed = time.time() - start
        reply = response.choices[0].message.content
        print(f"Reply: {reply}")
        print(f"Time: {elapsed:.2f}s")
        print("✅ Image input works!\n")
        return {"test": "image", "status": "ok", "elapsed_sec": round(elapsed, 2)}
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Image input failed: {e}")
        print("This is expected if Gemma vision isn't configured. Will use fallback.\n")
        return {"test": "image", "status": "failed", "error": str(e)}


def get_ram_usage():
    """Get RAM usage of Ollama process."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
        )
        ollama_lines = [l for l in result.stdout.split("\n") if "ollama" in l.lower()]
        return ollama_lines
    except Exception:
        return []


if __name__ == "__main__":
    print("\n🧪 Field Companion — Checkpoint 1.1 Verification\n")
    print(f"LLM_BASE_URL: {LLM_BASE_URL}")
    print(f"LLM_MODEL:    {LLM_MODEL}\n")

    results = []

    # Test text
    results.append(test_text())

    # Test image
    results.append(test_image())

    # RAM usage
    print("=" * 60)
    print("SYSTEM INFO")
    print("=" * 60)
    ram_lines = get_ram_usage()
    for line in ram_lines:
        print(f"  {line.strip()}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        status = "✅" if r.get("status", "ok") == "ok" else "❌"
        print(f"  {status} {r['test']}: {r.get('elapsed_sec', '?')}s")
        if r.get("tokens_per_sec"):
            print(f"     Tokens/sec: {r['tokens_per_sec']}")

    print("\nDone. Paste this output into NOTES.md for the checkpoint record.")
