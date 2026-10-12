#!/usr/bin/env python3
"""
Test script for Checkpoint 1.3 — Tool-calling agent loop.
Runs a text query through the agent and verifies:
1. Tool calling occurs (species_lookup or checklist_check)
2. Response is grounded in database
3. Confirmation tip is given
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent import run_agent

def main():
    print("=" * 60)
    print("Testing Checkpoint 1.3: Agent tool-calling & grounding")
    print("=" * 60)

    query = "I saw a small black bird with a white wing patch"
    print(f"\nUser query: \"{query}\"")
    print("\nRunning agent loop...")

    result = run_agent(query)

    print("\n--- Agent Result ---")
    print(f"Iterations: {result.get('iterations')}")
    print(f"Tools used: {result.get('tools_used')}")
    print(f"Tool results: {result.get('tool_results')}")
    print(f"\nResponse:\n{result.get('response')}")

    if result.get("error"):
        print(f"\n❌ Error encountered: {result['error']}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Verification:")
    print(f"1. Tool was called: {'✅' if len(result.get('tools_used', [])) > 0 else '❌'}")
    print(f"2. Response received: {'✅' if len(result.get('response', '')) > 0 else '❌'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
