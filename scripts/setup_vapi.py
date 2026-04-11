#!/usr/bin/env python3
"""Automated Vapi assistant setup via API.

Creates the Dr. Müller assistant with tools and voice config.
Requires VAPI_API_KEY environment variable.

Usage:
    python scripts/setup_vapi.py --webhook-url https://your-server.ngrok.io
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vapi import Vapi

from src.agent_config import TOOL_DEFINITIONS, get_assistant_config


def create_assistant(client: Vapi, webhook_url: str) -> str:
    """Create the Vapi assistant and return the assistant ID."""
    # Create tools first
    tool_ids = []
    for tool_def in TOOL_DEFINITIONS:
        func = tool_def["function"]
        tool = client.tools.create(
            request={
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": func["parameters"],
                },
                "server": {"url": f"{webhook_url}/api/vapi/webhook"},
            }
        )
        tool_ids.append(tool.id)
        print(f"  Created tool: {func['name']} (ID: {tool.id})")

    # Build config from single source of truth
    config = get_assistant_config(f"{webhook_url}/api/vapi/webhook")

    assistant = client.assistants.create(
        name=config["name"],
        first_message=config["firstMessage"],
        model={**config["model"], "toolIds": tool_ids},
        voice=config["voice"],
        server={"url": config["serverUrl"]},
        max_duration_seconds=config["maxDurationSeconds"],
        end_call_message=config["endCallMessage"],
    )

    return assistant.id


def main():
    parser = argparse.ArgumentParser(description="Setup Vapi Voice Agent")
    parser.add_argument(
        "--webhook-url",
        required=True,
        help="Public URL for webhook server (e.g. https://abc123.ngrok.io)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("VAPI_API_KEY")
    if not api_key:
        print("Error: VAPI_API_KEY environment variable not set.")
        print("Get your key from https://dashboard.vapi.ai/account")
        sys.exit(1)

    print(f"Setting up Vapi assistant...")
    print(f"  Webhook URL: {args.webhook_url}")

    client = Vapi(token=api_key)

    try:
        assistant_id = create_assistant(client, args.webhook_url)
        print(f"\nAssistant created successfully!")
        print(f"  Assistant ID: {assistant_id}")
        print(f"\nNext steps:")
        print(f"  1. Start webhook server: python src/main.py")
        print(f"  2. Assign a phone number in Vapi Dashboard")
        print(f"  3. Call the number to test!")
    except Exception as e:
        print(f"Error creating assistant: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
