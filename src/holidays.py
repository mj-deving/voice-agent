"""German holiday detection and office hours checking."""

from datetime import date, datetime, time

import yaml
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "availability.yaml"


def _load_holidays() -> dict[str, str]:
    """Load holidays from availability.yaml. Returns {YYYY-MM-DD: name} dict."""
    with open(_CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    holidays_list = config.get("holidays", [])
    return {h["date"]: h["name"] for h in holidays_list}


def is_holiday(check_date: date | None = None) -> tuple[bool, str | None]:
    """Check if a date is a holiday.

    Returns (True, "holiday name") or (False, None).
    """
    if check_date is None:
        check_date = date.today()
    holidays = _load_holidays()
    name = holidays.get(check_date.isoformat())
    if name:
        return True, name
    return False, None


def is_outside_hours(check_time: datetime | None = None) -> bool:
    """Check if the given datetime falls outside office hours.

    Uses availability.yaml office_hours config.
    """
    if check_time is None:
        check_time = datetime.now()

    with open(_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    day_name = check_time.strftime("%A").lower()
    hours = config.get("office_hours", {}).get(day_name)

    if hours is None:
        return True

    t = check_time.time()

    # Check morning block
    morning_start = hours.get("start")
    morning_end = hours.get("end")
    if morning_start and morning_end:
        start = time.fromisoformat(morning_start)
        end = time.fromisoformat(morning_end)
        if start <= t < end:
            return False

    # Check afternoon block
    afternoon_start = hours.get("afternoon_start")
    afternoon_end = hours.get("afternoon_end")
    if afternoon_start and afternoon_end:
        start = time.fromisoformat(afternoon_start)
        end = time.fromisoformat(afternoon_end)
        if start <= t < end:
            return False

    return True
