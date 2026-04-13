"""Appointment availability system for Praxis Dr. Muller."""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path

import yaml


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "availability.yaml"
_BOOKING_LOCK = threading.Lock()

# Cache config at module load — it doesn't change at runtime
_config: dict | None = None


def load_config() -> dict:
    """Read and return the availability configuration from YAML (cached)."""
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def _bookings_path(config: dict) -> Path:
    """Resolve the bookings file path from config."""
    p = Path(config["bookings_file"])
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    return p


def _get_bookings(config: dict) -> dict:
    """Load existing bookings from the JSON file."""
    path = _bookings_path(config)
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _save_bookings(config: dict, bookings: dict) -> None:
    """Write bookings dict to the JSON file."""
    path = _bookings_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)


def _generate_slots(hours: dict, duration: int) -> list[str]:
    """Generate time slots for given office hours block(s)."""
    slots: list[str] = []
    blocks = [("start", "end"), ("afternoon_start", "afternoon_end")]
    for start_key, end_key in blocks:
        if hours.get(start_key) and hours.get(end_key):
            start = datetime.strptime(hours[start_key], "%H:%M")
            end = datetime.strptime(hours[end_key], "%H:%M")
            current = start
            while current < end:
                slots.append(current.strftime("%H:%M"))
                current += timedelta(minutes=duration)
    return slots


def _day_name(date_str: str) -> str:
    """Return lowercase English day name for a YYYY-MM-DD date string."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%A").lower()


def get_available_slots(date: str, config: dict | None = None,
                        bookings: dict | None = None) -> list[str]:
    """Return available time slots (HH:MM) for a given date (YYYY-MM-DD).

    Accepts optional pre-loaded config/bookings to avoid redundant I/O.
    """
    if config is None:
        config = load_config()
    day = _day_name(date)
    hours = config["office_hours"].get(day)

    if hours is None:
        return []

    all_slots = _generate_slots(hours, config["slot_duration_minutes"])
    if bookings is None:
        bookings = _get_bookings(config)
    booked = set(bookings.get(date, {}).keys())

    return [s for s in all_slots if s not in booked]


def is_slot_available(date: str, time: str) -> bool:
    """Check if a specific slot is open for booking."""
    return time in get_available_slots(date)


def book_slot(date: str, time: str, patient_name: str) -> bool:
    """Book a slot atomically. Returns True on success, False if already booked."""
    config = load_config()

    with _BOOKING_LOCK:
        bookings = _get_bookings(config)
        booked = set(bookings.get(date, {}).keys())
        if time in booked:
            return False

        if date not in bookings:
            bookings[date] = {}
        bookings[date][time] = patient_name
        _save_bookings(config, bookings)
        return True


def get_next_available(date: str, time: str, count: int = 3) -> list[dict]:
    """Return next N available slots from the given date/time forward.

    Each result is a dict with 'date' and 'time' keys.
    """
    config = load_config()
    bookings = _get_bookings(config)

    results: list[dict] = []
    current_date = datetime.strptime(date, "%Y-%m-%d")
    start_time = time
    max_days = 60

    for _ in range(max_days):
        date_str = current_date.strftime("%Y-%m-%d")
        slots = get_available_slots(date_str, config=config, bookings=bookings)

        for slot in slots:
            if date_str == date and slot < start_time:
                continue
            results.append({"date": date_str, "time": slot})
            if len(results) >= count:
                return results

        current_date += timedelta(days=1)
        start_time = "00:00"

    return results
