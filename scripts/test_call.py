#!/usr/bin/env python3
"""Trigger test calls via Vapi API for defined scenarios.

Usage:
    python scripts/test_call.py                    # Run all scenarios
    python scripts/test_call.py --scenario 1       # Run specific scenario
    python scripts/test_call.py --list              # List available scenarios
"""

import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vapi import Vapi


def load_scenarios() -> list[dict]:
    """Load test scenarios from YAML config."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "scenarios.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["scenarios"]


def trigger_test_call(client: Vapi, assistant_id: str, scenario: dict) -> str:
    """Trigger a test call for a given scenario via Vapi web call."""
    print(f"\n--- Scenario {scenario['id']}: {scenario['name']} ---")
    print(f"  Caller: {scenario['caller']}")
    print(f"  Description: {scenario['description']}")
    print(f"  Expected action: {scenario['expected_action']}")

    # Create a web call (for testing without phone number)
    call = client.calls.create(
        assistant_id=assistant_id,
        customer={
            "name": scenario["caller"],
        },
    )

    print(f"  Call ID: {call.id}")
    print(f"  Status: {call.status}")
    print(f"  Dialog hints for manual testing:")
    for hint in scenario["dialog_hints"]:
        print(f"    > {hint}")

    return call.id


def main():
    parser = argparse.ArgumentParser(description="Test Voice Agent Scenarios")
    parser.add_argument("--scenario", type=int, help="Run specific scenario by ID")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--assistant-id", help="Vapi Assistant ID (or set VAPI_ASSISTANT_ID)")
    args = parser.parse_args()

    scenarios = load_scenarios()

    if args.list:
        print("Available test scenarios:")
        for s in scenarios:
            print(f"  {s['id']}. {s['name']} - {s['description']}")
            print(f"     Expected: {s['expected_action']}")
        return

    api_key = os.environ.get("VAPI_API_KEY")
    if not api_key:
        print("Error: VAPI_API_KEY not set")
        sys.exit(1)

    assistant_id = args.assistant_id or os.environ.get("VAPI_ASSISTANT_ID")
    if not assistant_id:
        print("Error: Assistant ID required. Use --assistant-id or set VAPI_ASSISTANT_ID")
        print("Run setup_vapi.py first to create the assistant.")
        sys.exit(1)

    client = Vapi(token=api_key)

    if args.scenario:
        scenario = next((s for s in scenarios if s["id"] == args.scenario), None)
        if not scenario:
            print(f"Error: Scenario {args.scenario} not found")
            sys.exit(1)
        trigger_test_call(client, assistant_id, scenario)
    else:
        print(f"Running all {len(scenarios)} test scenarios...")
        for scenario in scenarios:
            trigger_test_call(client, assistant_id, scenario)


if __name__ == "__main__":
    main()
