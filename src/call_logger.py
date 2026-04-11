"""Call event logging to JSON file."""

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "data"
LOG_FILE = LOG_DIR / "call_log.jsonl"

# Create log directory once at import time
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_call_event(
    event_type: str,
    caller_name: str | None = None,
    action: str | None = None,
    details: dict | None = None,
) -> dict:
    """Log a call event to the JSONL log file.

    Returns the logged entry.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "caller_name": caller_name,
        "action": action,
        "details": details or {},
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry
