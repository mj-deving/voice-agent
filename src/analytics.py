"""Call analytics — reads call_log.jsonl and computes dashboard metrics."""

import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from src.call_logger import LOG_FILE


def _parse_event_date(timestamp: str) -> date | None:
    """Parse an ISO timestamp string to a date, or None on failure."""
    try:
        return datetime.fromisoformat(timestamp).date()
    except (ValueError, TypeError):
        return None


def load_events(
    log_path: Path | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    """Load call events from JSONL, optionally filtered by date range."""
    path = log_path or LOG_FILE
    if not path.exists():
        return []

    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if date_from or date_to:
                event_date = _parse_event_date(entry.get("timestamp", ""))
                if event_date is None:
                    continue
                if date_from and event_date < date_from:
                    continue
                if date_to and event_date > date_to:
                    continue

            events.append(entry)

    return events


def compute_metrics(events: list[dict]) -> dict:
    """Compute analytics metrics from a list of call events in a single pass."""
    today = date.today()

    calls_total = 0
    calls_today = 0
    durations: list[float] = []
    calls_per_day: Counter[str] = Counter()
    tool_call_count = 0
    booking_count = 0
    reasons: Counter[str] = Counter()

    for e in events:
        event_type = e.get("event_type")

        if event_type == "end_of_call":
            calls_total += 1
            event_date = _parse_event_date(e.get("timestamp", ""))
            if event_date:
                if event_date == today:
                    calls_today += 1
                calls_per_day[event_date.isoformat()] += 1
            d = e.get("details", {}).get("duration")
            if d is not None:
                try:
                    durations.append(float(d))
                except (ValueError, TypeError):
                    pass

        elif event_type == "tool_call":
            tool_call_count += 1
            if e.get("action") == "book_appointment":
                booking_count += 1
                reason = e.get("details", {}).get("reason", "")
                if reason:
                    reasons[reason] += 1

    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0
    booking_rate = round(booking_count / tool_call_count * 100, 1) if tool_call_count else 0.0

    return {
        "calls_total": calls_total,
        "calls_today": calls_today,
        "avg_duration_sec": avg_duration,
        "booking_rate": booking_rate,
        "top_reasons": reasons.most_common(10),
        "calls_per_day": dict(sorted(calls_per_day.items())),
    }


def get_analytics(
    date_from: date | None = None,
    date_to: date | None = None,
    log_path: Path | None = None,
) -> dict:
    """Load events and compute metrics — main entry point."""
    events = load_events(log_path=log_path, date_from=date_from, date_to=date_to)
    return compute_metrics(events)
