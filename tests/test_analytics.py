"""Tests for call analytics module."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.analytics import compute_metrics, get_analytics, load_events
from src.webhook_server import app


def _write_jsonl(tmp_path: Path, entries: list[dict]) -> Path:
    """Write test entries to a temporary JSONL file."""
    log_file = tmp_path / "call_log.jsonl"
    with open(log_file, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return log_file


SAMPLE_EVENTS = [
    {
        "timestamp": "2026-04-14T09:00:00+00:00",
        "event_type": "tool_call",
        "caller_name": "Thomas Schneider",
        "action": "book_appointment",
        "details": {"reason": "Rückenschmerzen", "date": "2026-04-15", "time": "09:00"},
    },
    {
        "timestamp": "2026-04-14T09:05:00+00:00",
        "event_type": "end_of_call",
        "caller_name": None,
        "action": None,
        "details": {"duration": 120, "ended_reason": "completed"},
    },
    {
        "timestamp": "2026-04-14T10:00:00+00:00",
        "event_type": "tool_call",
        "caller_name": "Maria Weber",
        "action": "transfer_call",
        "details": {"destination": "praxis", "reason": "Rezept"},
    },
    {
        "timestamp": "2026-04-14T10:05:00+00:00",
        "event_type": "end_of_call",
        "caller_name": None,
        "action": None,
        "details": {"duration": 90, "ended_reason": "completed"},
    },
    {
        "timestamp": "2026-04-13T14:00:00+00:00",
        "event_type": "tool_call",
        "caller_name": "Hans Müller",
        "action": "book_appointment",
        "details": {"reason": "Kopfschmerzen", "date": "2026-04-14", "time": "10:00"},
    },
    {
        "timestamp": "2026-04-13T14:05:00+00:00",
        "event_type": "end_of_call",
        "caller_name": None,
        "action": None,
        "details": {"duration": 180, "ended_reason": "completed"},
    },
    {
        "timestamp": "2026-04-14T11:00:00+00:00",
        "event_type": "tool_call",
        "caller_name": "Anna Schmidt",
        "action": "book_appointment",
        "details": {"reason": "Rückenschmerzen", "date": "2026-04-16", "time": "14:00"},
    },
    {
        "timestamp": "2026-04-14T11:05:00+00:00",
        "event_type": "end_of_call",
        "caller_name": None,
        "action": None,
        "details": {"duration": 60, "ended_reason": "completed"},
    },
]


class TestLoadEvents:
    def test_load_from_file(self, tmp_path):
        log_file = _write_jsonl(tmp_path, SAMPLE_EVENTS)
        events = load_events(log_path=log_file)
        assert len(events) == 8

    def test_load_missing_file_returns_empty(self, tmp_path):
        events = load_events(log_path=tmp_path / "nonexistent.jsonl")
        assert events == []

    def test_load_empty_file_returns_empty(self, tmp_path):
        log_file = tmp_path / "empty.jsonl"
        log_file.write_text("")
        events = load_events(log_path=log_file)
        assert events == []

    def test_load_skips_malformed_lines(self, tmp_path):
        log_file = tmp_path / "bad.jsonl"
        log_file.write_text('{"valid": true}\nnot json\n{"also": "valid"}\n')
        events = load_events(log_path=log_file)
        assert len(events) == 2

    def test_date_from_filter(self, tmp_path):
        log_file = _write_jsonl(tmp_path, SAMPLE_EVENTS)
        events = load_events(log_path=log_file, date_from=date(2026, 4, 14))
        # Should exclude 2026-04-13 events (2 entries)
        assert len(events) == 6

    def test_date_to_filter(self, tmp_path):
        log_file = _write_jsonl(tmp_path, SAMPLE_EVENTS)
        events = load_events(log_path=log_file, date_to=date(2026, 4, 13))
        assert len(events) == 2

    def test_date_range_filter(self, tmp_path):
        log_file = _write_jsonl(tmp_path, SAMPLE_EVENTS)
        events = load_events(
            log_path=log_file,
            date_from=date(2026, 4, 14),
            date_to=date(2026, 4, 14),
        )
        assert len(events) == 6


class TestComputeMetrics:
    def test_calls_total(self):
        metrics = compute_metrics(SAMPLE_EVENTS)
        assert metrics["calls_total"] == 4

    @patch("src.analytics.date")
    def test_calls_today(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 14)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        metrics = compute_metrics(SAMPLE_EVENTS)
        assert metrics["calls_today"] == 3

    def test_avg_duration(self):
        metrics = compute_metrics(SAMPLE_EVENTS)
        # (120 + 90 + 180 + 60) / 4 = 112.5
        assert metrics["avg_duration_sec"] == 112.5

    def test_booking_rate(self):
        metrics = compute_metrics(SAMPLE_EVENTS)
        # 3 book_appointment out of 4 tool_calls = 75%
        assert metrics["booking_rate"] == 75.0

    def test_top_reasons(self):
        metrics = compute_metrics(SAMPLE_EVENTS)
        reasons = dict(metrics["top_reasons"])
        assert reasons["Rückenschmerzen"] == 2
        assert reasons["Kopfschmerzen"] == 1

    def test_calls_per_day(self):
        metrics = compute_metrics(SAMPLE_EVENTS)
        per_day = metrics["calls_per_day"]
        assert per_day["2026-04-13"] == 1
        assert per_day["2026-04-14"] == 3

    def test_empty_events(self):
        metrics = compute_metrics([])
        assert metrics["calls_total"] == 0
        assert metrics["avg_duration_sec"] == 0.0
        assert metrics["booking_rate"] == 0.0
        assert metrics["top_reasons"] == []
        assert metrics["calls_per_day"] == {}


class TestGetAnalytics:
    def test_get_analytics_returns_all_fields(self, tmp_path):
        log_file = _write_jsonl(tmp_path, SAMPLE_EVENTS)
        result = get_analytics(log_path=log_file)
        assert "calls_total" in result
        assert "calls_today" in result
        assert "avg_duration_sec" in result
        assert "booking_rate" in result
        assert "top_reasons" in result
        assert "calls_per_day" in result

    def test_get_analytics_with_date_filter(self, tmp_path):
        log_file = _write_jsonl(tmp_path, SAMPLE_EVENTS)
        result = get_analytics(
            date_from=date(2026, 4, 14),
            log_path=log_file,
        )
        # Only 2026-04-14 events: 3 end_of_call
        assert result["calls_total"] == 3


class TestAnalyticsEndpoint:
    def setup_method(self):
        self.client = TestClient(app)

    @patch("src.webhook_server.get_analytics")
    def test_analytics_endpoint_returns_200(self, mock_analytics):
        mock_analytics.return_value = {
            "calls_total": 10,
            "calls_today": 3,
            "avg_duration_sec": 120.0,
            "booking_rate": 50.0,
            "top_reasons": [["Rückenschmerzen", 5]],
            "calls_per_day": {"2026-04-14": 3},
        }
        response = self.client.get("/api/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["calls_total"] == 10

    @patch("src.webhook_server.get_analytics")
    def test_analytics_endpoint_passes_date_params(self, mock_analytics):
        mock_analytics.return_value = {"calls_total": 0, "calls_today": 0,
                                        "avg_duration_sec": 0, "booking_rate": 0,
                                        "top_reasons": [], "calls_per_day": {}}
        self.client.get("/api/analytics?from=2026-04-01&to=2026-04-14")
        mock_analytics.assert_called_once_with(
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 14),
        )

    @patch("src.webhook_server.get_analytics")
    def test_analytics_endpoint_no_params(self, mock_analytics):
        mock_analytics.return_value = {"calls_total": 0, "calls_today": 0,
                                        "avg_duration_sec": 0, "booking_rate": 0,
                                        "top_reasons": [], "calls_per_day": {}}
        self.client.get("/api/analytics")
        mock_analytics.assert_called_once_with(date_from=None, date_to=None)
