"""Tests for holiday detection and dynamic greetings."""

from datetime import date, datetime, time
from unittest.mock import patch

from src.holidays import is_holiday, is_outside_hours
from src.agent_config import build_first_message


# --- Holiday detection ---

class TestIsHoliday:
    def test_neujahr_is_holiday(self):
        result, name = is_holiday(date(2026, 1, 1))
        assert result is True
        assert name == "Neujahr"

    def test_karfreitag_is_holiday(self):
        result, name = is_holiday(date(2026, 4, 3))
        assert result is True
        assert name == "Karfreitag"

    def test_ostermontag_is_holiday(self):
        result, name = is_holiday(date(2026, 4, 6))
        assert result is True
        assert name == "Ostermontag"

    def test_tag_der_arbeit_is_holiday(self):
        result, name = is_holiday(date(2026, 5, 1))
        assert result is True
        assert name == "Tag der Arbeit"

    def test_christi_himmelfahrt_is_holiday(self):
        result, name = is_holiday(date(2026, 5, 14))
        assert result is True
        assert name == "Christi Himmelfahrt"

    def test_pfingstmontag_is_holiday(self):
        result, name = is_holiday(date(2026, 5, 25))
        assert result is True
        assert name == "Pfingstmontag"

    def test_tag_der_einheit_is_holiday(self):
        result, name = is_holiday(date(2026, 10, 3))
        assert result is True
        assert name == "Tag der Deutschen Einheit"

    def test_weihnachten_1_is_holiday(self):
        result, name = is_holiday(date(2026, 12, 25))
        assert result is True
        assert name == "1. Weihnachtstag"

    def test_weihnachten_2_is_holiday(self):
        result, name = is_holiday(date(2026, 12, 26))
        assert result is True
        assert name == "2. Weihnachtstag"

    def test_normal_weekday_not_holiday(self):
        result, name = is_holiday(date(2026, 4, 14))
        assert result is False
        assert name is None

    def test_weekend_not_holiday(self):
        result, name = is_holiday(date(2026, 4, 11))
        assert result is False
        assert name is None


class TestBavarianHolidays:
    def test_heilige_drei_koenige(self):
        result, name = is_holiday(date(2026, 1, 6))
        assert result is True
        assert name == "Heilige Drei Könige"

    def test_fronleichnam(self):
        result, name = is_holiday(date(2026, 6, 4))
        assert result is True
        assert name == "Fronleichnam"

    def test_mariae_himmelfahrt(self):
        result, name = is_holiday(date(2026, 8, 15))
        assert result is True
        assert name == "Mariä Himmelfahrt"

    def test_allerheiligen(self):
        result, name = is_holiday(date(2026, 11, 1))
        assert result is True
        assert name == "Allerheiligen"


# --- Office hours checking ---

class TestIsOutsideHours:
    def test_monday_morning_inside(self):
        dt = datetime(2026, 4, 13, 9, 0)  # Monday 09:00
        assert is_outside_hours(dt) is False

    def test_monday_afternoon_inside(self):
        dt = datetime(2026, 4, 13, 15, 0)  # Monday 15:00
        assert is_outside_hours(dt) is False

    def test_monday_lunch_outside(self):
        dt = datetime(2026, 4, 13, 12, 30)  # Monday 12:30 (lunch break)
        assert is_outside_hours(dt) is True

    def test_monday_evening_outside(self):
        dt = datetime(2026, 4, 13, 19, 0)  # Monday 19:00
        assert is_outside_hours(dt) is True

    def test_monday_early_morning_outside(self):
        dt = datetime(2026, 4, 13, 7, 0)  # Monday 07:00
        assert is_outside_hours(dt) is True

    def test_saturday_outside(self):
        dt = datetime(2026, 4, 11, 10, 0)  # Saturday 10:00
        assert is_outside_hours(dt) is True

    def test_sunday_outside(self):
        dt = datetime(2026, 4, 12, 10, 0)  # Sunday 10:00
        assert is_outside_hours(dt) is True

    def test_friday_morning_start_boundary(self):
        dt = datetime(2026, 4, 17, 8, 0)  # Friday 08:00 exactly
        assert is_outside_hours(dt) is False

    def test_friday_morning_end_boundary(self):
        dt = datetime(2026, 4, 17, 12, 0)  # Friday 12:00 exactly (end = exclusive)
        assert is_outside_hours(dt) is True


# --- Dynamic greetings ---

MOCK_CONFIG = {
    "praxis_name": "Praxis Dr. Müller",
    "arzt_name": "Dr. Sarah Müller",
    "begruessung": "Praxis Dr. Müller, hier spricht Lisa. Wie kann ich Ihnen helfen?",
    "oeffnungszeiten": "Mo-Fr 8:00-12:00 und 14:00-18:00 Uhr",
    "notfall_nummer": "112",
}


class TestBuildFirstMessage:
    def test_holiday_greeting(self):
        # Karfreitag 2026
        now = datetime(2026, 4, 3, 10, 0)
        msg = build_first_message(MOCK_CONFIG, now=now)
        assert "Karfreitag" in msg
        assert "geschlossen" in msg
        assert "112" in msg

    def test_outside_hours_greeting(self):
        # Monday 20:00
        now = datetime(2026, 4, 13, 20, 0)
        msg = build_first_message(MOCK_CONFIG, now=now)
        assert "derzeit geschlossen" in msg
        assert "Öffnungszeiten" in msg
        assert "Mo-Fr" in msg

    def test_normal_hours_greeting(self):
        # Monday 10:00
        now = datetime(2026, 4, 13, 10, 0)
        msg = build_first_message(MOCK_CONFIG, now=now)
        assert msg == MOCK_CONFIG["begruessung"]

    def test_holiday_takes_precedence_over_hours(self):
        # Neujahr at 10:00 (would be "inside hours" on a Thursday)
        now = datetime(2026, 1, 1, 10, 0)
        msg = build_first_message(MOCK_CONFIG, now=now)
        assert "Neujahr" in msg
        assert "geschlossen" in msg

    def test_weekend_outside_hours(self):
        # Saturday 10:00
        now = datetime(2026, 4, 11, 10, 0)
        msg = build_first_message(MOCK_CONFIG, now=now)
        assert "derzeit geschlossen" in msg
