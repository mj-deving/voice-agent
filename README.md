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
echo "VAPI_API_KEY=your-key-here" > .env

# 3. Create Vapi Assistant
python scripts/setup_vapi.py --webhook-url https://your-tunnel.ngrok.io

# 4. Start webhook server
python src/main.py
```

## What It Does

Lisa, die KI-Assistentin der Praxis Dr. Sarah Müller, beantwortet eingehende Anrufe auf Deutsch:

- Begrüßt Anrufer und fragt nach dem Anliegen
- Unterscheidet neue und bestehende Patienten
- Bucht Termine (via `book_appointment` Tool)
- Leitet an die Praxis weiter bei Rezepten/Überweisungen (`transfer_call`)
- Erkennt Notfälle und empfiehlt sofort 112
- Sendet Zusammenfassungen ans Praxisteam (`send_summary`)
- Beantwortet Fragen zu Öffnungszeiten und Adresse

## Architecture

```
[Eingehender Anruf]
        │
        ▼
┌─ Vapi Agent (Lisa) ──────────────────────┐
│  Model: Claude Sonnet (Anthropic)        │
│  Voice: ElevenLabs (Deutsch)             │
│  System Prompt: Praxis Dr. Müller        │
│                                          │
│  Tools:                                  │
│  - book_appointment ──┐                  │
│  - transfer_call ─────┤ Webhook ────┐    │
│  - send_summary ──────┘             │    │
└──────────────────────────────────────┘    │
                                           ▼
                              ┌─ FastAPI Server ─┐
                              │ /api/vapi/webhook │
                              │                   │
                              │ → Handle tool     │
                              │   calls           │
                              │ → Log to JSONL    │
                              └───────────────────┘
```

## Project Structure

```
voice-agent-mvp/
├── src/
│   ├── main.py              # Entry point — starts webhook server
│   ├── agent_config.py      # System prompt, tools, voice/model config
│   ├── webhook_server.py    # FastAPI server for Vapi tool calls
│   └── call_logger.py       # JSONL call logging
├── scripts/
│   ├── setup_vapi.py        # Automated Vapi assistant setup via API
│   └── test_call.py         # Trigger test calls for 5 scenarios
├── configs/
│   └── scenarios.yaml       # 5 test scenarios (Termin, Rezept, Notfall, etc.)
├── tests/
│   ├── test_agent_config.py # 42 tests for agent configuration
│   └── test_webhook.py      # 21 tests for webhook endpoints
└── data/
    └── call_log.jsonl       # Call event log (auto-created)
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

```
VAPI_API_KEY=your-vapi-api-key
VAPI_ASSISTANT_ID=your-assistant-id
HOST=0.0.0.0
PORT=8000
DEBUG=true  # enables auto-reload
```

## Tests

```bash
pytest tests/ -v
# 64 tests covering agent config + webhook server
```

## Costs

| Component | Cost |
|-----------|------|
| Vapi Free Tier | $10 credits (~200 min) |
| Phone Number | ~$1/month |
| Claude Sonnet (via Vapi) | ~$0.01-0.03/call |
| **5 Test Calls** | **~$0.50** |

## License

MIT
