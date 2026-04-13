"""Tests for Vapi webhook server — tool call handling."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.webhook_server import app

client = TestClient(app)


# --- Health check ---

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# --- Webhook: book_appointment ---

class TestBookAppointment:
    def _make_payload(self, **params):
        defaults = {
            "patient_name": "Thomas Schneider",
            "date": "2026-04-14",
            "time": "09:00",
            "reason": "Rückenschmerzen",
        }
        defaults.update(params)
        return {
            "message": {
                "type": "function-call",
                "functionCall": {
                    "name": "book_appointment",
                    "parameters": defaults,
                },
            }
        }

    @patch("src.webhook_server.book_slot", return_value=True)
    @patch("src.webhook_server.is_slot_available", return_value=True)
    @patch("src.webhook_server.log_call_event")
    def test_book_appointment_returns_200(self, mock_log, _mock_avail, _mock_book):
        mock_log.return_value = {}
        response = client.post("/api/vapi/webhook", json=self._make_payload())
        assert response.status_code == 200

    @patch("src.webhook_server.book_slot", return_value=True)
    @patch("src.webhook_server.is_slot_available", return_value=True)
    @patch("src.webhook_server.log_call_event")
    def test_book_appointment_returns_confirmation(self, mock_log, _mock_avail, _mock_book):
        mock_log.return_value = {}
        response = client.post("/api/vapi/webhook", json=self._make_payload())
        result = response.json()["result"]
        assert "Termin erfolgreich gebucht" in result
        assert "Thomas Schneider" in result

    @patch("src.webhook_server.book_slot", return_value=True)
    @patch("src.webhook_server.is_slot_available", return_value=True)
    @patch("src.webhook_server.log_call_event")
    def test_book_appointment_includes_date_and_time(self, mock_log, _mock_avail, _mock_book):
        mock_log.return_value = {}
        response = client.post("/api/vapi/webhook", json=self._make_payload())
        result = response.json()["result"]
        assert "2026-04-14" in result
        assert "09:00" in result

    @patch("src.webhook_server.book_slot", return_value=True)
    @patch("src.webhook_server.is_slot_available", return_value=True)
    @patch("src.webhook_server.log_call_event")
    def test_book_appointment_new_patient_label(self, mock_log, _mock_avail, _mock_book):
        mock_log.return_value = {}
        response = client.post(
            "/api/vapi/webhook",
            json=self._make_payload(is_new_patient=True),
        )
        result = response.json()["result"]
        assert "neuer Patient" in result

    @patch("src.webhook_server.book_slot", return_value=True)
    @patch("src.webhook_server.is_slot_available", return_value=True)
    @patch("src.webhook_server.log_call_event")
    def test_book_appointment_existing_patient_label(self, mock_log, _mock_avail, _mock_book):
        mock_log.return_value = {}
        response = client.post(
            "/api/vapi/webhook",
            json=self._make_payload(is_new_patient=False),
        )
        result = response.json()["result"]
        assert "Patient" in result
        assert "neuer Patient" not in result

    @patch("src.webhook_server.book_slot", return_value=True)
    @patch("src.webhook_server.is_slot_available", return_value=True)
    @patch("src.webhook_server.log_call_event")
    def test_book_appointment_logs_event(self, mock_log, _mock_avail, _mock_book):
        mock_log.return_value = {}
        client.post("/api/vapi/webhook", json=self._make_payload())
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args
        assert call_kwargs.kwargs["action"] == "book_appointment"
        assert call_kwargs.kwargs["caller_name"] == "Thomas Schneider"


# --- Webhook: transfer_call ---

class TestTransferCall:
    def _make_payload(self, **params):
        defaults = {"destination": "praxis", "reason": "Rezept-Nachbestellung"}
        defaults.update(params)
        return {
            "message": {
                "type": "function-call",
                "functionCall": {
                    "name": "transfer_call",
                    "parameters": defaults,
                },
            }
        }

    @patch("src.webhook_server.log_call_event")
    def test_transfer_call_returns_200(self, mock_log):
        mock_log.return_value = {}
        response = client.post("/api/vapi/webhook", json=self._make_payload())
        assert response.status_code == 200

    @patch("src.webhook_server.log_call_event")
    def test_transfer_call_includes_destination(self, mock_log):
        mock_log.return_value = {}
        response = client.post("/api/vapi/webhook", json=self._make_payload())
        result = response.json()["result"]
        assert "praxis" in result

    @patch("src.webhook_server.log_call_event")
    def test_transfer_call_includes_reason(self, mock_log):
        mock_log.return_value = {}
        response = client.post("/api/vapi/webhook", json=self._make_payload())
        result = response.json()["result"]
        assert "Rezept-Nachbestellung" in result

    @patch("src.webhook_server.log_call_event")
    def test_transfer_call_logs_event(self, mock_log):
        mock_log.return_value = {}
        client.post("/api/vapi/webhook", json=self._make_payload())
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args
        assert call_kwargs.kwargs["action"] == "transfer_call"


# --- Webhook: send_summary ---

class TestSendSummary:
    def _make_payload(self, **params):
        defaults = {
            "summary": "Pharma-Vertreter möchte Termin mit Ärztin",
            "caller_name": "Dr. Fischer",
            "action_required": True,
        }
        defaults.update(params)
        return {
            "message": {
                "type": "function-call",
                "functionCall": {
                    "name": "send_summary",
                    "parameters": defaults,
                },
            }
        }

    @patch("src.webhook_server.log_call_event")
    def test_send_summary_returns_200(self, mock_log):
        mock_log.return_value = {}
        response = client.post("/api/vapi/webhook", json=self._make_payload())
        assert response.status_code == 200

    @patch("src.webhook_server.log_call_event")
    def test_send_summary_confirms_sent(self, mock_log):
        mock_log.return_value = {}
        response = client.post("/api/vapi/webhook", json=self._make_payload())
        result = response.json()["result"]
        assert "Zusammenfassung gesendet" in result

    @patch("src.webhook_server.log_call_event")
    def test_send_summary_action_required_flag(self, mock_log):
        mock_log.return_value = {}
        response = client.post(
            "/api/vapi/webhook",
            json=self._make_payload(action_required=True),
        )
        result = response.json()["result"]
        assert "Aktion erforderlich" in result

    @patch("src.webhook_server.log_call_event")
    def test_send_summary_no_action_required(self, mock_log):
        mock_log.return_value = {}
        response = client.post(
            "/api/vapi/webhook",
            json=self._make_payload(action_required=False),
        )
        result = response.json()["result"]
        assert "Aktion erforderlich" not in result

    @patch("src.webhook_server.log_call_event")
    def test_send_summary_logs_event(self, mock_log):
        mock_log.return_value = {}
        client.post("/api/vapi/webhook", json=self._make_payload())
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args
        assert call_kwargs.kwargs["action"] == "send_summary"
        assert call_kwargs.kwargs["caller_name"] == "Dr. Fischer"


# --- Webhook: malformed requests ---

class TestMalformedRequests:
    def test_unknown_function_returns_400(self):
        payload = {
            "message": {
                "type": "function-call",
                "functionCall": {
                    "name": "unknown_function",
                    "parameters": {},
                },
            }
        }
        response = client.post("/api/vapi/webhook", json=payload)
        assert response.status_code == 400

    def test_missing_message_type_returns_ignored(self):
        response = client.post("/api/vapi/webhook", json={"message": {}})
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_status_update_returns_received(self):
        payload = {"message": {"type": "status-update", "status": "in-progress"}}
        response = client.post("/api/vapi/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "received"


# --- Webhook: end-of-call ---

class TestEndOfCall:
    @patch("src.webhook_server.log_call_event")
    def test_end_of_call_returns_logged(self, mock_log):
        mock_log.return_value = {}
        payload = {
            "message": {
                "type": "end-of-call-report",
                "durationSeconds": 120,
                "endedReason": "completed",
                "summary": "Patient hat Termin gebucht",
            }
        }
        response = client.post("/api/vapi/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "logged"

    @patch("src.webhook_server.log_call_event")
    def test_end_of_call_logs_duration(self, mock_log):
        mock_log.return_value = {}
        payload = {
            "message": {
                "type": "end-of-call-report",
                "durationSeconds": 120,
                "endedReason": "completed",
            }
        }
        client.post("/api/vapi/webhook", json=payload)
        mock_log.assert_called_once()
        details = mock_log.call_args.kwargs["details"]
        assert details["duration"] == 120
        assert details["ended_reason"] == "completed"
