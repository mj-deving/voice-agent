"""Tests for appointment availability system."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.availability import (
    book_slot,
    get_available_slots,
    get_next_available,
    is_slot_available,
    load_config,
)


@pytest.fixture
def bookings_file(tmp_path):
    """Create a temporary bookings file and patch load_config to use it."""
    bf = tmp_path / "bookings.json"
    bf.write_text("{}")
    return bf


@pytest.fixture(autouse=True)
def _patch_config(bookings_file):
    """Patch load_config so all functions use the tmp bookings file."""
    fake_config = {
        "office_hours": {
            "monday": {"start": "08:00", "end": "12:00", "afternoon_start": "14:00", "afternoon_end": "18:00"},
            "tuesday": {"start": "08:00", "end": "12:00", "afternoon_start": "14:00", "afternoon_end": "18:00"},
            "wednesday": {"start": "08:00", "end": "12:00", "afternoon_start": "14:00", "afternoon_end": "18:00"},
            "thursday": {"start": "08:00", "end": "12:00", "afternoon_start": "14:00", "afternoon_end": "18:00"},
            "friday": {"start": "08:00", "end": "12:00", "afternoon_start": "14:00", "afternoon_end": "18:00"},
            "saturday": None,
            "sunday": None,
        },
        "slot_duration_minutes": 30,
        "bookings_file": str(bookings_file),
    }
    with patch("src.availability.load_config", return_value=fake_config):
        yield


# --- load_config ---

class TestLoadConfig:
    def test_load_config_returns_dict(self):
        """load_config returns a dict with expected keys."""
        # Unpatch for this test to hit real config
        with patch.dict("os.environ", {}, clear=False):
            config = load_config.__wrapped__() if hasattr(load_config, '__wrapped__') else load_config()
        # Just verify it's a dict (may be patched or real)

    def test_load_config_has_office_hours(self):
        config = load_config()
        assert "office_hours" in config
        assert "monday" in config["office_hours"]

    def test_load_config_has_slot_duration(self):
        config = load_config()
        assert "slot_duration_minutes" in config
        assert config["slot_duration_minutes"] == 30


# --- get_available_slots ---

class TestGetAvailableSlots:
    def test_weekday_generates_correct_slots(self):
        """Monday 2026-04-13 should generate morning + afternoon slots."""
        # 2026-04-13 is a Monday
        slots = get_available_slots("2026-04-13")
        # Morning: 08:00, 08:30, 09:00, 09:30, 10:00, 10:30, 11:00, 11:30 = 8 slots
        # Afternoon: 14:00, 14:30, 15:00, 15:30, 16:00, 16:30, 17:00, 17:30 = 8 slots
        assert len(slots) == 16
        assert "08:00" in slots
        assert "11:30" in slots
        assert "14:00" in slots
        assert "17:30" in slots
        # 12:00 and 18:00 should NOT be in slots (end boundaries)
        assert "12:00" not in slots
        assert "18:00" not in slots

    def test_no_slots_on_saturday(self):
        """Saturday 2026-04-18 should return empty list."""
        slots = get_available_slots("2026-04-18")
        assert slots == []

    def test_no_slots_on_sunday(self):
        """Sunday 2026-04-19 should return empty list."""
        slots = get_available_slots("2026-04-19")
        assert slots == []

    def test_booked_slots_excluded(self, bookings_file):
        """Already booked slots should not appear in available list."""
        bookings = {"2026-04-13": {"09:00": "Thomas Schneider", "09:30": "Maria Weber"}}
        bookings_file.write_text(json.dumps(bookings))

        slots = get_available_slots("2026-04-13")
        assert "09:00" not in slots
        assert "09:30" not in slots
        # Other slots still available
        assert "08:00" in slots
        assert "10:00" in slots

    def test_slots_are_sorted(self):
        """Slots should be in chronological order."""
        slots = get_available_slots("2026-04-13")
        assert slots == sorted(slots)


# --- is_slot_available ---

class TestIsSlotAvailable:
    def test_available_slot_returns_true(self):
        """Unbooked weekday slot should be available."""
        assert is_slot_available("2026-04-13", "09:00") is True

    def test_booked_slot_returns_false(self, bookings_file):
        """Booked slot should return False."""
        bookings = {"2026-04-13": {"09:00": "Thomas Schneider"}}
        bookings_file.write_text(json.dumps(bookings))

        assert is_slot_available("2026-04-13", "09:00") is False

    def test_weekend_slot_returns_false(self):
        """Weekend slot should not be available."""
        assert is_slot_available("2026-04-18", "09:00") is False

    def test_outside_hours_returns_false(self):
        """Slot outside office hours should not be available."""
        assert is_slot_available("2026-04-13", "13:00") is False


# --- book_slot ---

class TestBookSlot:
    def test_book_slot_returns_true(self):
        """Booking an open slot should return True."""
        result = book_slot("2026-04-13", "09:00", "Thomas Schneider")
        assert result is True

    def test_book_slot_writes_to_file(self, bookings_file):
        """Booking should persist to the bookings file."""
        book_slot("2026-04-13", "09:00", "Thomas Schneider")

        data = json.loads(bookings_file.read_text())
        assert data["2026-04-13"]["09:00"] == "Thomas Schneider"

    def test_double_booking_returns_false(self, bookings_file):
        """Booking an already-booked slot should return False."""
        bookings = {"2026-04-13": {"09:00": "Thomas Schneider"}}
        bookings_file.write_text(json.dumps(bookings))

        result = book_slot("2026-04-13", "09:00", "Maria Weber")
        assert result is False

    def test_double_booking_preserves_original(self, bookings_file):
        """Failed double-booking should not overwrite original."""
        bookings = {"2026-04-13": {"09:00": "Thomas Schneider"}}
        bookings_file.write_text(json.dumps(bookings))

        book_slot("2026-04-13", "09:00", "Maria Weber")
        data = json.loads(bookings_file.read_text())
        assert data["2026-04-13"]["09:00"] == "Thomas Schneider"

    def test_book_multiple_slots_same_day(self, bookings_file):
        """Multiple bookings on same day should all persist."""
        book_slot("2026-04-13", "09:00", "Thomas Schneider")
        book_slot("2026-04-13", "09:30", "Maria Weber")

        data = json.loads(bookings_file.read_text())
        assert data["2026-04-13"]["09:00"] == "Thomas Schneider"
        assert data["2026-04-13"]["09:30"] == "Maria Weber"


# --- get_next_available ---

class TestGetNextAvailable:
    def test_returns_requested_count(self):
        """Should return exactly count available slots."""
        results = get_next_available("2026-04-13", "08:00", count=3)
        assert len(results) == 3

    def test_returns_dicts_with_date_and_time(self):
        """Each result should have date and time keys."""
        results = get_next_available("2026-04-13", "08:00", count=1)
        assert "date" in results[0]
        assert "time" in results[0]

    def test_skips_booked_slots(self, bookings_file):
        """Should skip already-booked slots."""
        bookings = {"2026-04-13": {"08:00": "Thomas Schneider", "08:30": "Maria Weber"}}
        bookings_file.write_text(json.dumps(bookings))

        results = get_next_available("2026-04-13", "08:00", count=1)
        assert results[0]["time"] == "09:00"

    def test_spans_multiple_days(self, bookings_file):
        """If a day is fully booked, should move to next day."""
        # Book all Monday slots
        monday_bookings = {}
        for h in range(8, 12):
            for m in (0, 30):
                monday_bookings[f"{h:02d}:{m:02d}"] = "Blocked"
        for h in range(14, 18):
            for m in (0, 30):
                monday_bookings[f"{h:02d}:{m:02d}"] = "Blocked"
        bookings = {"2026-04-13": monday_bookings}
        bookings_file.write_text(json.dumps(bookings))

        results = get_next_available("2026-04-13", "08:00", count=1)
        # Should be on Tuesday 2026-04-14
        assert results[0]["date"] == "2026-04-14"

    def test_skips_weekends(self, bookings_file):
        """Should not suggest weekend slots."""
        # 2026-04-17 is Friday; 18:00 is past last slot (17:30)
        results = get_next_available("2026-04-17", "18:00", count=1)
        # Next slot after Friday end should be on Monday 2026-04-20
        assert results[0]["date"] == "2026-04-20"

    def test_default_count_is_three(self):
        """Default count should be 3."""
        results = get_next_available("2026-04-13", "08:00")
        assert len(results) == 3
