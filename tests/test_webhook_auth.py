"""Tests for HMAC webhook signature verification."""

import hashlib
import hmac
import json
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.webhook_server import app

client = TestClient(app)


class TestHmacAuthDisabled:
    """When VAPI_WEBHOOK_SECRET is not set, all requests pass through."""

    def test_webhook_passes_without_secret(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VAPI_WEBHOOK_SECRET", None)
            response = client.get("/health")
            assert response.status_code == 200

    @patch("src.webhook_server.log_call_event")
    def test_webhook_post_passes_without_secret(self, mock_log):
        mock_log.return_value = {}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VAPI_WEBHOOK_SECRET", None)
            payload = {"message": {"type": "status-update", "status": "in-progress"}}
            response = client.post("/api/vapi/webhook", json=payload)
            assert response.status_code == 200


class TestHmacAuthEnabled:
    """When VAPI_WEBHOOK_SECRET is set, signatures are verified."""

    SECRET = "test-webhook-secret-123"

    def _sign(self, body: bytes) -> str:
        return hmac.new(self.SECRET.encode(), body, hashlib.sha256).hexdigest()

    def test_health_bypasses_auth(self):
        with patch.dict(os.environ, {"VAPI_WEBHOOK_SECRET": self.SECRET}):
            response = client.get("/health")
            assert response.status_code == 200

    def test_missing_signature_returns_401(self):
        with patch.dict(os.environ, {"VAPI_WEBHOOK_SECRET": self.SECRET}):
            payload = {"message": {"type": "status-update"}}
            response = client.post("/api/vapi/webhook", json=payload)
            assert response.status_code == 401
            assert "Missing signature" in response.json()["detail"]

    def test_invalid_signature_returns_401(self):
        with patch.dict(os.environ, {"VAPI_WEBHOOK_SECRET": self.SECRET}):
            payload = {"message": {"type": "status-update"}}
            response = client.post(
                "/api/vapi/webhook",
                json=payload,
                headers={"x-vapi-signature": "invalid-signature"},
            )
            assert response.status_code == 401
            assert "Invalid signature" in response.json()["detail"]

    @patch("src.webhook_server.log_call_event")
    def test_valid_signature_passes(self, mock_log):
        mock_log.return_value = {}
        with patch.dict(os.environ, {"VAPI_WEBHOOK_SECRET": self.SECRET}):
            payload = {"message": {"type": "status-update", "status": "in-progress"}}
            body = json.dumps(payload).encode()
            sig = self._sign(body)
            response = client.post(
                "/api/vapi/webhook",
                content=body,
                headers={
                    "x-vapi-signature": sig,
                    "content-type": "application/json",
                },
            )
            assert response.status_code == 200


class TestTransferDestination:
    """Tests for transfer-destination-request handling."""

    @patch("src.webhook_server.log_call_event")
    def test_transfer_destination_returns_number(self, mock_log):
        mock_log.return_value = {}
        payload = {
            "message": {
                "type": "transfer-destination-request",
                "destination": "praxis",
            }
        }
        response = client.post("/api/vapi/webhook", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["destination"]["type"] == "number"
        assert data["destination"]["number"] is not None

    @patch("src.webhook_server.log_call_event")
    def test_transfer_destination_includes_message(self, mock_log):
        mock_log.return_value = {}
        payload = {
            "message": {
                "type": "transfer-destination-request",
                "destination": "praxis",
            }
        }
        response = client.post("/api/vapi/webhook", json=payload)
        data = response.json()
        assert "verbinde" in data["destination"]["message"]

    @patch("src.webhook_server.log_call_event")
    def test_transfer_destination_logs_event(self, mock_log):
        mock_log.return_value = {}
        payload = {
            "message": {
                "type": "transfer-destination-request",
                "destination": "labor",
            }
        }
        client.post("/api/vapi/webhook", json=payload)
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "transfer_call"
