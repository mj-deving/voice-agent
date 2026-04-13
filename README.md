# Voice Agent MVP — Praxis Dr. Müller

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**KI-Telefonagent für eine Arztpraxis — nimmt Anrufe entgegen, qualifiziert Anrufer, bucht Termine und leitet weiter.**

## Quick Start

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env  # then fill in your keys

# 3. Create Vapi Assistant
python scripts/setup_vapi.py --webhook-url https://your-tunnel.ngrok.io

# 4. Start webhook server
python src/main.py
```

## What It Does

Lisa, die KI-Assistentin der Praxis Dr. Sarah Müller, beantwortet eingehende Anrufe auf Deutsch:

- Begrüßt Anrufer und fragt nach dem Anliegen
- Unterscheidet neue und bestehende Patienten
- Bucht Termine mit Verfügbarkeitsprüfung (`book_appointment`) — schlägt Alternativen vor wenn belegt
- Leitet Anrufe an die Praxis weiter bei Rezepten/Überweisungen (`transfer_call`) — echte Telefonweiterleitung via Vapi
- Erkennt Notfälle und empfiehlt sofort 112
- Sendet Zusammenfassungen ans Praxisteam per E-Mail und/oder Webhook (`send_summary`)
- Beantwortet Fragen zu Öffnungszeiten und Adresse

## Architecture

```
[Eingehender Anruf]
        │
        ▼
┌─ Vapi Agent (Lisa) ──────────────────────┐
│  Model: Claude Sonnet 4 (Anthropic)      │
│  Voice: ElevenLabs (Deutsch)             │
│  System Prompt: Praxis Dr. Müller        │
│                                          │
│  Tools:                                  │
│  - book_appointment ──┐                  │
│  - transfer_call ─────┤ Webhook ────┐    │
│  - send_summary ──────┘             │    │
└──────────────────────────────────────┘    │
                                           ▼
                         ┌─ FastAPI Server ──────────┐
                         │ /api/vapi/webhook          │
                         │                            │
                         │ → HMAC signature verify    │
                         │ → Route tool calls         │
                         │ → Check availability       │
                         │ → Book appointments        │
                         │ → Transfer calls (SIP)     │
                         │ → Notify team (email/hook) │
                         │ → Log to JSONL             │
                         └────────────────────────────┘
```

## Project Structure

```
voice-agent-mvp/
├── src/
│   ├── main.py              # Entry point — starts webhook server
│   ├── agent_config.py      # System prompt, tools, voice/model config
│   ├── webhook_server.py    # FastAPI server for Vapi tool calls
│   ├── webhook_auth.py      # HMAC-SHA256 signature verification middleware
│   ├── availability.py      # Appointment slot checking & booking
│   ├── notifications.py     # Email (SMTP) + webhook notification dispatch
│   └── call_logger.py       # JSONL call logging
├── scripts/
│   ├── setup_vapi.py        # Automated Vapi assistant + tools + phone setup
│   └── test_call.py         # Trigger test calls for 5 scenarios
├── configs/
│   ├── scenarios.yaml       # 5 test scenarios (Termin, Rezept, Notfall, etc.)
│   └── availability.yaml    # Office hours, slot duration, bookings path
├── tests/                   # 108 tests
│   ├── test_agent_config.py # Agent configuration (42 tests)
│   ├── test_webhook.py      # Webhook endpoints (22 tests)
│   ├── test_availability.py # Availability system (23 tests)
│   ├── test_notifications.py# Notification dispatch (12 tests)
│   └── test_webhook_auth.py # HMAC auth + transfer (9 tests)
├── data/
│   ├── call_log.jsonl       # Call event log (auto-created)
│   └── bookings.json        # Booked appointments (auto-created)
├── Dockerfile               # Production container
├── fly.toml                 # Fly.io deployment config
└── docker-compose.yml       # Local Docker deployment
```

## Test Scenarios

| # | Scenario | Expected Action |
|---|----------|----------------|
| 1 | Neuer Patient, Rückenschmerzen | `book_appointment` |
| 2 | Bestandspatient, Rezept | `transfer_call` |
| 3 | Notfall, Brustschmerzen | 112 empfehlen |
| 4 | Frage zu Öffnungszeiten | Info direkt geben |
| 5 | Pharma-Vertreter | `send_summary` |

```bash
# List scenarios
python scripts/test_call.py --list

# Run specific scenario
python scripts/test_call.py --scenario 1 --assistant-id <ID>
```

## Configuration

Set in `.env`:

```bash
# Required
VAPI_API_KEY=your-vapi-api-key

# Webhook auth (optional — disabled if not set)
VAPI_WEBHOOK_SECRET=your-hmac-secret

# Transfer destination
PRAXIS_PHONE_NUMBER=+498912345678

# Email notifications (optional — skipped if not set)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=praxis@example.com
SMTP_PASSWORD=app-password
NOTIFICATION_EMAIL_TO=team@example.com
NOTIFICATION_EMAIL_FROM=lisa@example.com

# Webhook notifications (optional — skipped if not set)
NOTIFICATION_WEBHOOK_URL=https://hooks.slack.com/services/...

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

## Setup

```bash
# Basic — creates assistant with tools
python scripts/setup_vapi.py --webhook-url https://your-tunnel.ngrok.io

# With webhook auth
python scripts/setup_vapi.py --webhook-url https://... --webhook-secret my-secret

# With phone number provisioning
python scripts/setup_vapi.py --webhook-url https://... --phone-number
```

## Deployment

```bash
# Docker
docker compose up --build

# Fly.io (Frankfurt region)
fly deploy
```

## Tests

```bash
pytest tests/ -v
# 108 tests covering agent config, webhook server, availability, notifications, auth
```

## Costs

| Component | Cost |
|-----------|------|
| Vapi Free Tier | $10 credits (~200 min) |
| Phone Number | ~$1/month |
| Claude Sonnet 4 (via Vapi) | ~$0.01-0.03/call |
| **5 Test Calls** | **~$0.50** |

## License

MIT
