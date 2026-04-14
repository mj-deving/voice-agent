# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

KI-Telefonagent MVP using Vapi.ai for a German medical practice (Arztpraxis Dr. Müller). The agent "Lisa" answers calls, qualifies callers, books appointments, transfers calls, and detects emergencies.

## Commands

```bash
source venv/bin/activate

# Start webhook server (default port 8000)
python src/main.py

# Run all tests
pytest tests/ -v

# Run single test file
pytest tests/test_webhook.py -v

# Run single test
pytest tests/test_webhook.py::TestBookAppointment::test_book_appointment_returns_confirmation -v

# Setup Vapi assistant (requires VAPI_API_KEY in .env and a public URL)
python scripts/setup_vapi.py --webhook-url https://your-tunnel.ngrok.io

# List test scenarios
python scripts/test_call.py --list

# Trigger test call (requires VAPI_ASSISTANT_ID)
python scripts/test_call.py --scenario 1
```

## Architecture

Vapi.ai handles voice (STT/TTS) and LLM orchestration. When the LLM decides to use a tool, Vapi sends a webhook to our FastAPI server. The server processes the tool call and returns a result string that the LLM speaks back to the caller.

```
Caller → Vapi (voice + LLM) → webhook POST /api/vapi/webhook → FastAPI handlers → response string → Vapi → Caller
```

Key flow: Vapi sends `message.type: "function-call"` with `message.functionCall.name` and `message.functionCall.parameters`. The webhook routes to the matching handler via the `FUNCTION_HANDLERS` dict in `webhook_server.py`, which logs the event and returns a German-language result string.

**agent_config.py** is the single source of truth for all Vapi configuration (system prompt, voice, model, tool definitions). **setup_vapi.py** consumes it via `get_assistant_config()` to create the assistant on Vapi's API. When adding a new tool: define it in `TOOL_DEFINITIONS` (agent_config.py), add a handler function in `webhook_server.py`, and register it in `FUNCTION_HANDLERS`.

The webhook handles these message types: `function-call` (routed to handlers), `transfer-destination-request` (returns phone number), `end-of-call-report` (logged), `status-update` (acknowledged).

Additional endpoints: `GET /api/analytics` (call metrics with optional `?from=&to=` date filter), `GET /static/dashboard.html` (Chart.js dashboard UI).

**Key modules:**
- `agent_config.py` — loads praxis config from YAML (`configs/examples/`), generates system prompt, first message, and tool definitions. Module-level constants (`SYSTEM_PROMPT`, `FIRST_MESSAGE`, `TOOL_DEFINITIONS`) load default Mueller config for backward compat. New praxis = new YAML file + `--config` flag on setup_vapi.py.
- `analytics.py` — reads `data/call_log.jsonl`, computes dashboard metrics (calls total/today, avg duration, booking rate, top reasons, calls/day). Single-pass computation. Supports date range filtering.
- `availability.py` — reads `configs/availability.yaml` for office hours, checks/books slots, persists bookings to `data/bookings.json`
- `notifications.py` — dispatches call summaries via email (SMTP) and/or webhook (httpx POST). Channels configured via env vars, unconfigured channels silently skip.
- `webhook_auth.py` — HMAC-SHA256 middleware verifying `x-vapi-signature` header. Disabled when `VAPI_WEBHOOK_SECRET` not set. Bypasses `/health`.

## Deployment

```bash
# Docker
docker compose up --build

# Fly.io
fly deploy
```

Env vars for production: `VAPI_API_KEY`, `VAPI_WEBHOOK_SECRET`, `PRAXIS_PHONE_NUMBER`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `NOTIFICATION_EMAIL_TO`, `NOTIFICATION_EMAIL_FROM`, `NOTIFICATION_WEBHOOK_URL`.

## Stack

- Python 3.12+, FastAPI, uvicorn
- `vapi-server-sdk` for Vapi API (assistant/tool CRUD) — NOT `vapi-python` (that's client-side only)
- API keys loaded from `~/.claude/.env` or local `.env` (first match wins, checked in that order)
- Tests use `fastapi.testclient.TestClient` (sync) with `@patch("src.webhook_server.log_call_event")` to avoid file I/O
- Analytics tests use `tmp_path` JSONL fixtures; endpoint tests mock `get_analytics`

## Conventions

- Type hints on all public functions
- One module per concern — keep files under 300 lines
- Tests mirror src/ structure: `src/agent.py` → `tests/test_agent.py`
- Test classes group by feature (e.g. `TestBookAppointment`, `TestTransferCall`) with `_make_payload()` helpers
- Configs in YAML, not hardcoded
- All user-facing text in German (system prompt, tool responses, call messages)
- Webhook handlers return plain German strings (Vapi speaks them to caller)
- Call events logged as JSONL to `data/call_log.jsonl`
