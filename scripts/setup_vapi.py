#!/usr/bin/env python3
"""Automated Vapi assistant setup via API.

Creates the Dr. Müller assistant with tools and voice config.
Requires VAPI_API_KEY environment variable.

Usage:
    python scripts/setup_vapi.py --webhook-url https://your-server.ngrok.io
    python scripts/setup_vapi.py --webhook-url https://your-server.ngrok.io --phone-number
    python scripts/setup_vapi.py --webhook-url https://your-server.ngrok.io --webhook-secret my-secret
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vapi import Vapi

from src.agent_config import build_tool_definitions, get_assistant_config, load_praxis_config


def create_tools(client: Vapi, webhook_url: str, tool_defs: list[dict]) -> list[str]:
    """Create tools on Vapi and return their IDs."""
    tool_ids = []
    for tool_def in tool_defs:
        func = tool_def["function"]
        request = {
            "type": tool_def["type"],
            "function": {
                "name": func["name"],
                "description": func["description"],
                "parameters": func["parameters"],
            },
            "server": {"url": f"{webhook_url}/api/vapi/webhook"},
        }
        if "destinations" in tool_def:
            request["destinations"] = tool_def["destinations"]

        tool = client.tools.create(request=request)
        tool_ids.append(tool.id)
        print(f"  Created tool: {func['name']} ({tool_def['type']}, ID: {tool.id})")

    return tool_ids


def create_hmac_credential(client: Vapi, secret: str) -> str | None:
    """Create an HMAC credential for webhook signature verification.

    Returns the credential ID, or None if creation fails.
    """
    try:
        credential = client.credentials.create(
            request={
                "provider": "custom",
                "name": "webhook-hmac-secret",
                "authenticationPlan": {
                    "type": "hmac",
                    "secretKey": secret,
                    "algorithm": "sha256",
                    "signatureHeader": "x-vapi-signature",
                },
            }
        )
        return credential.id
    except Exception as e:
        print(f"  Warning: Could not create HMAC credential: {e}")
        print("  Configure webhook secret manually in Vapi Dashboard.")
        return None


def create_assistant(client: Vapi, webhook_url: str, tool_ids: list[str],
                     credential_id: str | None = None,
                     praxis_config: dict | None = None) -> str:
    """Create the Vapi assistant and return the assistant ID."""
    config = get_assistant_config(f"{webhook_url}/api/vapi/webhook", praxis_config)

    server_config = {"url": config["serverUrl"]}
    if credential_id:
        server_config["credentialId"] = credential_id

    assistant = client.assistants.create(
        name=config["name"],
        first_message=config["firstMessage"],
        model={**config["model"], "toolIds": tool_ids},
        voice=config["voice"],
        server=server_config,
        max_duration_seconds=config["maxDurationSeconds"],
        end_call_message=config["endCallMessage"],
    )

    return assistant.id


def provision_phone_number(client: Vapi, assistant_id: str) -> str | None:
    """Provision a Vapi phone number and assign it to the assistant.

    Returns the phone number, or None if provisioning fails.
    """
    try:
        phone = client.phone_numbers.create(
            request={
                "type": "vapi",
                "assistantId": assistant_id,
            }
        )
        return phone.number
    except Exception as e:
        print(f"  Warning: Could not provision phone number: {e}")
        print("  Assign a phone number manually in Vapi Dashboard.")
        return None


def main():
    parser = argparse.ArgumentParser(description="Setup Vapi Voice Agent")
    parser.add_argument(
        "--webhook-url",
        required=True,
        help="Public URL for webhook server (e.g. https://abc123.ngrok.io)",
    )
    parser.add_argument(
        "--phone-number",
        action="store_true",
        help="Provision a Vapi phone number and assign to assistant",
    )
    parser.add_argument(
        "--webhook-secret",
        help="HMAC secret for webhook signature verification",
    )
    parser.add_argument(
        "--config",
        help="Path to praxis YAML config (default: configs/examples/praxis_mueller.yaml)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("VAPI_API_KEY")
    if not api_key:
        print("Error: VAPI_API_KEY environment variable not set.")
        print("Get your key from https://dashboard.vapi.ai/account")
        sys.exit(1)

    praxis_config = load_praxis_config(args.config)
    print("Setting up Vapi assistant...")
    print(f"  Praxis: {praxis_config['praxis_name']}")
    print(f"  Webhook URL: {args.webhook_url}")

    client = Vapi(token=api_key)
    tool_defs = build_tool_definitions(praxis_config)

    try:
        # Create HMAC credential if secret provided
        credential_id = None
        if args.webhook_secret:
            print("\nCreating HMAC credential...")
            credential_id = create_hmac_credential(client, args.webhook_secret)
            if credential_id:
                print(f"  Credential ID: {credential_id}")

        # Create tools
        print("\nCreating tools...")
        tool_ids = create_tools(client, args.webhook_url, tool_defs)

        # Create assistant
        print("\nCreating assistant...")
        assistant_id = create_assistant(client, args.webhook_url, tool_ids,
                                        credential_id, praxis_config)
        print(f"  Assistant ID: {assistant_id}")

        # Provision phone number if requested
        phone = None
        if args.phone_number:
            print("\nProvisioning phone number...")
            phone = provision_phone_number(client, assistant_id)
            if phone:
                print(f"  Phone number: {phone}")

        print("\nSetup complete!")
        print(f"  Assistant ID: {assistant_id}")
        if phone:
            print(f"  Phone number: {phone}")
        if args.webhook_secret:
            print(f"\n  Set VAPI_WEBHOOK_SECRET={args.webhook_secret} in your .env")

        print("\nNext steps:")
        print("  1. Start webhook server: python src/main.py")
        if not phone:
            print("  2. Assign a phone number in Vapi Dashboard")
        print("  3. Call the number to test!")

    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
