#!/usr/bin/env python3
"""
Field Companion — Audio Evaluation Test Runner (Checkpoint 2.1)
Runs 10 known bird recordings through the audio identification pipeline.
Measures:
- Top-1 and Top-3 accuracy
- Hit rate
- Median and mean latency
- Pretty prints markdown summary table for PROGRESS.md and NOTES.md
"""

import os
import sys
import time
import json
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.audio import analyze_bird_audio
from app.agent import run_agent

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "../eval/audio")
MANIFEST_PATH = os.path.join(AUDIO_DIR, "manifest.json")


def run_audio_eval():
    print("=" * 70)
    print("Field Companion — Checkpoint 2.1 Audio Test (10 Known Clips)")
    print("=" * 70)

    if not os.path.exists(MANIFEST_PATH):
        print(f"Error: {MANIFEST_PATH} not found.")
        return

    with open(MANIFEST_PATH, "r") as f:
        samples = json.load(f)

    print(f"Loaded {len(samples)} benchmark audio clips.\n")

    results = []
    latencies = []
    top1_matches = 0
    top3_matches = 0

    for idx, item in enumerate(samples, 1):
        filename = item["filename"]
        expected = item["common_name"]
        expected_sci = item["sci_name"]
        audio_path = os.path.join(AUDIO_DIR, filename)

        print(f"[{idx}/10] Testing '{filename}' (Expected: {expected})...")
        t0 = time.time()
        detections = analyze_bird_audio(audio_path)
        elapsed = time.time() - t0
        latencies.append(elapsed)

        top1 = detections[0]["common_name"] if len(detections) > 0 else "None"
        top3 = [d["common_name"] for d in detections[:3]]

        is_top1 = (expected.lower() == top1.lower())
        is_top3 = any(expected.lower() == cand.lower() for cand in top3)

        if is_top1:
            top1_matches += 1
        if is_top3:
            top3_matches += 1

        top_conf = detections[0]["confidence"] if detections else 0.0
        source = detections[0].get("source", "Unknown") if detections else "None"

        print(f"       -> Top-1: {top1} (conf: {top_conf}) | Top-3 match: {'✅' if is_top3 else '❌'} | Time: {elapsed:.3f}s")

        results.append({
            "idx": idx,
            "filename": filename,
            "expected": expected,
            "sci_name": expected_sci,
            "detected_top1": top1,
            "detected_top3": top3,
            "confidence": top_conf,
            "is_top1": is_top1,
            "is_top3": is_top3,
            "latency_s": round(elapsed, 3),
            "source": source,
        })

    # Summary metrics
    n = len(samples)
    top1_acc = (top1_matches / n) * 100
    top3_acc = (top3_matches / n) * 100
    med_latency = statistics.median(latencies)
    mean_latency = statistics.mean(latencies)

    print("\n" + "=" * 70)
    print("AUDIO BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Total samples tested:  {n}")
    print(f"Top-1 Accuracy:        {top1_acc:.1f}% ({top1_matches}/{n})")
    print(f"Top-3 Accuracy:        {top3_acc:.1f}% ({top3_matches}/{n})")
    print(f"Median Latency:        {med_latency:.3f}s")
    print(f"Mean Latency:          {mean_latency:.3f}s")
    print("=" * 70 + "\n")

    # Generate Markdown Table
    md_table = """### Checkpoint 2.1 — 10 Known Audio Sample Test Results

| # | Expected Species | Scientific Name | Top-1 Detected | Top-3 Match | Confidence | Latency | Source |
|---|---|---|---|:---:|---|---|---|
"""
    for r in results:
        top3_icon = "✅" if r["is_top3"] else "❌"
        md_table += f"| {r['idx']} | {r['expected']} | *{r['sci_name']}* | {r['detected_top1']} | {top3_icon} | {r['confidence']:.2f} | {r['latency_s']}s | {r['source']} |\n"

    md_table += f"""
**Summary Metrics:**
- **Top-1 Hit Rate:** {top1_acc:.1f}% ({top1_matches}/{n})
- **Top-3 Hit Rate:** {top3_acc:.1f}% ({top3_matches}/{n})
- **Median Latency:** {med_latency:.3f}s (Mean: {mean_latency:.3f}s)
- **Fallback Architecture:** Acoustic feature extraction (peak frequency, spectral centroid) with checklist grounding.
"""

    print(md_table)
    return results, md_table


if __name__ == "__main__":
    run_audio_eval()
