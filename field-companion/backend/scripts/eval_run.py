#!/usr/bin/env python3
"""
Field Companion — Evaluation Harness (Checkpoint 2.4)
Runs evaluation test set, computes:
- Top-1 and Top-3 accuracy
- 'Not sure' rate (honest hedging)
- Hallucination count (species named that were absent from DB checklist)
- Median & mean latency per query
- Pretty prints markdown results table suitable for project README / write-up
"""

import os
import sys
import csv
import time
import statistics
from typing import List, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent import run_agent
from app.db import get_species_by_name

LABELS_CSV = os.path.join(os.path.dirname(__file__), "../eval/labels.csv")

def evaluate(max_samples: int = 15):
    print("=" * 70)
    print("Field Companion — Running Evaluation Harness")
    print("=" * 70)

    if not os.path.exists(LABELS_CSV):
        print(f"Error: {LABELS_CSV} not found.")
        return

    with open(LABELS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    # Filter text evaluation rows
    test_rows = [r for r in all_rows if r["type"] == "text"][:max_samples]
    print(f"Evaluating {len(test_rows)} test cases...\n")

    latencies = []
    top1_correct = 0
    top3_correct = 0
    not_sure_count = 0
    hallucination_count = 0
    results_detail = []

    for idx, row in enumerate(test_rows, 1):
        query = row["query"]
        expected = row["expected_species"]
        expected_sci = row.get("expected_sci", "")

        print(f"[{idx}/{len(test_rows)}] Testing: \"{query}\"")
        start = time.time()
        agent_out = run_agent(query)
        elapsed = time.time() - start
        latencies.append(elapsed)

        response_text = agent_out.get("response", "")
        tools_used = agent_out.get("tools_used", [])
        tool_results = agent_out.get("tool_results", [])

        # Check 'not sure'
        is_not_sure = any(phrase in response_text.lower() for phrase in ["not sure", "need more", "unclear", "cannot identify", "could not find"])
        if is_not_sure:
            not_sure_count += 1

        # Check species named in tool outputs
        species_in_tools = set()
        for tr in tool_results:
            r = tr.get("result", {})
            if isinstance(r, dict):
                if r.get("common_name"):
                    species_in_tools.add(r["common_name"].lower())
                for c in r.get("candidates", []):
                    if c.get("common_name"):
                        species_in_tools.add(c["common_name"].lower())

        # Check accuracy against expected
        is_top1 = False
        is_top3 = False

        if expected.lower() in response_text.lower():
            is_top1 = True
            is_top3 = True
            top1_correct += 1
            top3_correct += 1
        elif expected_sci and expected_sci.lower() in response_text.lower():
            is_top1 = True
            is_top3 = True
            top1_correct += 1
            top3_correct += 1
        else:
            # Check if expected was among tool candidates
            for sp in species_in_tools:
                if expected.lower() in sp or sp in expected.lower():
                    is_top3 = True
                    top3_correct += 1
                    break

        # Check hallucination: did response mention a species that isn't in DB?
        # A species is considered hallucinated if mentioned as identified but absent from DB
        hallucinated = False
        if not is_not_sure and not is_top3:
            # Check if any named claim exists in DB
            has_db_match = False
            for word in response_text.split():
                if len(word) > 4 and get_species_by_name(word):
                    has_db_match = True
                    break
            if not has_db_match and len(tools_used) == 0:
                hallucinated = True
                hallucination_count += 1

        status_sym = "✅" if is_top1 else ("🟡" if is_top3 else ("❓" if is_not_sure else "❌"))
        print(f"       -> {status_sym} Latency: {elapsed:.2f}s | Iterations: {agent_out.get('iterations')} | Tools: {tools_used}")

        results_detail.append({
            "id": row["id"],
            "query": query,
            "expected": expected,
            "status": status_sym,
            "latency": round(elapsed, 2),
            "response": response_text[:80] + "...",
        })

    # Summary calculations
    total = len(test_rows)
    top1_acc = (top1_correct / total) * 100 if total else 0
    top3_acc = (top3_correct / total) * 100 if total else 0
    not_sure_rate = (not_sure_count / total) * 100 if total else 0
    median_lat = statistics.median(latencies) if latencies else 0
    mean_lat = statistics.mean(latencies) if latencies else 0

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS SUMMARY TABLE")
    print("=" * 70)
    print(f"| Metric | Result |")
    print(f"|---|---|")
    print(f"| Total evaluated queries | {total} |")
    print(f"| Top-1 Accuracy | {top1_acc:.1f}% ({top1_correct}/{total}) |")
    print(f"| Top-3 Accuracy | {top3_acc:.1f}% ({top3_correct}/{total}) |")
    print(f"| 'Not sure' / Hedging rate | {not_sure_rate:.1f}% ({not_sure_count}/{total}) |")
    print(f"| Hallucinated species count | {hallucination_count} |")
    print(f"| Median latency | {median_lat:.2f} s |")
    print(f"| Mean latency | {mean_lat:.2f} s |")
    print("=" * 70)
    print("\nPaste this Markdown summary table directly into your report / write-up.")

if __name__ == "__main__":
    samples = 5
    if len(sys.argv) > 1:
        samples = int(sys.argv[1])
    evaluate(max_samples=samples)
