"""Tests for notification delivery (email + webhook)."""

import os
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from src.notifications import send_notification


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove all notification env vars so each test starts clean."""
    for key in (
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
        "NOTIFICATION_EMAIL_TO", "NOTIFICATION_EMAIL_FROM",
        "NOTIFICATION_WEBHOOK_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def _set_smtp_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("NOTIFICATION_EMAIL_TO", "praxis@example.com")
    monkeypatch.setenv("NOTIFICATION_EMAIL_FROM", "lisa@example.com")


def _set_webhook_env(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_WEBHOOK_URL", "https://hooks.example.com/notify")


def _mock_smtp():
    """Create a mock SMTP instance that works as context manager."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestEmailChannel:
    def test_email_sent_when_configured(self, monkeypatch):
        _set_smtp_env(monkeypatch)
        mock_smtp = _mock_smtp()
        with patch("src.notifications.smtplib.SMTP", return_value=mock_smtp):
            result = send_notification("Test summary", "Dr. Fischer", True)
        assert result["email"] is True
        mock_smtp.send_message.assert_called_once()

    def test_email_skipped_when_not_configured(self):
        result = send_notification("Test", "Test Caller", False)
        assert result["email"] is False

    def test_email_skipped_partial_config(self, monkeypatch):
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        result = send_notification("Test", "Test Caller", False)
        assert result["email"] is False

    def test_email_failure_returns_false(self, monkeypatch):
        _set_smtp_env(monkeypatch)
        with patch("src.notifications.smtplib.SMTP", side_effect=smtplib.SMTPException("fail")):
            result = send_notification("Test", "Test Caller", False)
        assert result["email"] is False


class TestWebhookChannel:
    def test_webhook_sent_when_configured(self, monkeypatch):
        _set_webhook_env(monkeypatch)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("src.notifications.httpx.post", return_value=mock_response) as mock_post:
            result = send_notification("Test summary", "Dr. Fischer", True)
        assert result["webhook"] is True
        mock_post.assert_called_once()

    def test_webhook_skipped_when_not_configured(self):
        result = send_notification("Test", "Test Caller", False)
        assert result["webhook"] is False

    def test_webhook_failure_returns_false(self, monkeypatch):
        _set_webhook_env(monkeypatch)
        with patch("src.notifications.httpx.post", side_effect=Exception("Network error")):
            result = send_notification("Test", "Test Caller", False)
        assert result["webhook"] is False

    def test_webhook_payload_has_fields(self, monkeypatch):
        _set_webhook_env(monkeypatch)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("src.notifications.httpx.post", return_value=mock_response) as mock_post:
            send_notification("Patient braucht Rezept", "Dr. Fischer", True)
        payload = mock_post.call_args.kwargs["json"]
        assert payload["caller_name"] == "Dr. Fischer"
        assert payload["summary"] == "Patient braucht Rezept"
        assert payload["action_required"] is True
        assert "timestamp" in payload


class TestBothChannels:
    def test_both_succeed(self, monkeypatch):
        _set_smtp_env(monkeypatch)
        _set_webhook_env(monkeypatch)
        mock_smtp = _mock_smtp()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("src.notifications.smtplib.SMTP", return_value=mock_smtp), \
             patch("src.notifications.httpx.post", return_value=mock_response):
            result = send_notification("Test", "Dr. Fischer", True)
        assert result == {"email": True, "webhook": True}

    def test_email_failure_doesnt_block_webhook(self, monkeypatch):
        _set_smtp_env(monkeypatch)
        _set_webhook_env(monkeypatch)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("src.notifications.smtplib.SMTP", side_effect=smtplib.SMTPException("fail")), \
             patch("src.notifications.httpx.post", return_value=mock_response):
            result = send_notification("Test", "Caller", False)
        assert result["email"] is False
        assert result["webhook"] is True

    def test_webhook_failure_doesnt_block_email(self, monkeypatch):
        _set_smtp_env(monkeypatch)
        _set_webhook_env(monkeypatch)
        mock_smtp = _mock_smtp()
        with patch("src.notifications.smtplib.SMTP", return_value=mock_smtp), \
             patch("src.notifications.httpx.post", side_effect=Exception("fail")):
            result = send_notification("Test", "Caller", False)
        assert result["email"] is True
        assert result["webhook"] is False

    def test_both_skipped_when_unconfigured(self):
        result = send_notification("Test", "Caller", False)
        assert result == {"email": False, "webhook": False}
