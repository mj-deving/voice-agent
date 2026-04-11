"""Main entry point — starts the Vapi webhook server."""

import os
from pathlib import Path

import uvicorn


def load_env():
    """Load API keys from ~/.claude/.env or local .env"""
    env_paths = [
        Path.home() / ".claude" / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())
            break


def main():
    load_env()

    if not os.environ.get("VAPI_API_KEY"):
        print("Warning: VAPI_API_KEY not set. Webhook server will run but setup/test scripts won't work.")
        print("Set it with: export VAPI_API_KEY=your-key-here")

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))

    print(f"Starting Vapi webhook server on {host}:{port}")
    print(f"Webhook endpoint: http://{host}:{port}/api/vapi/webhook")
    print(f"Health check: http://{host}:{port}/health")

    uvicorn.run(
        "src.webhook_server:app",
        host=host,
        port=port,
        reload=os.environ.get("DEBUG", "").lower() in ("1", "true"),
    )


if __name__ == "__main__":
    main()
