"""Vapi Agent configuration for Arztpraxis Dr. Müller."""

SYSTEM_PROMPT = """Du bist Lisa, die KI-Assistentin der Praxis Dr. Sarah Müller, Fachärztin \
für Allgemeinmedizin in München.

Deine Aufgaben:
1. Begrüße den Anrufer freundlich und frage nach dem Anliegen
2. Finde heraus: Neuer oder bestehender Patient?
3. Erfasse: Name, Geburtsdatum (bei neuen Patienten), Anliegen/Beschwerden
4. Bei Terminwunsch: Schlage verfügbare Zeiten vor und buche mit dem book_appointment Tool
5. Bei Notfall (Brustschmerzen, Atemnot, starke Blutung, Bewusstlosigkeit): \
Sofort empfehlen den Notruf 112 anzurufen. Keinen Termin buchen, keine Weiterleitung.
6. Bei Rezepten/Überweisungen: An die Praxis weiterleiten mit transfer_call
7. Bei allgemeinen Fragen (Öffnungszeiten, Adresse): Direkt beantworten
8. Fasse am Ende zusammen was vereinbart wurde

Wichtige Informationen:
- Öffnungszeiten: Mo-Fr 8:00-12:00 und 14:00-18:00 Uhr
- Adresse: Marienplatz 5, 80331 München
- Telefon Praxis: 089-12345678
- Notfallnummer: 112

Ton: Freundlich, professionell, empathisch. Sprich immer Deutsch.
Halte dich kurz und präzise. Frage immer nur eine Sache auf einmal."""

FIRST_MESSAGE = (
    "Praxis Dr. Müller, hier spricht Lisa, die digitale Assistentin. "
    "Wie kann ich Ihnen helfen?"
)

VOICE_CONFIG = {
    "provider": "11labs",
    "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Rachel - natural German-capable voice
    "stability": 0.7,
    "similarityBoost": 0.8,
    "language": "de",
}

MODEL_CONFIG = {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.3,
    "maxTokens": 300,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Bucht einen Termin für den Patienten in der Praxis Dr. Müller",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {
                        "type": "string",
                        "description": "Vollständiger Name des Patienten",
                    },
                    "date": {
                        "type": "string",
                        "description": "Gewünschtes Datum im Format YYYY-MM-DD",
                    },
                    "time": {
                        "type": "string",
                        "description": "Gewünschte Uhrzeit im Format HH:MM",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Grund des Termins / Beschwerden",
                    },
                    "is_new_patient": {
                        "type": "boolean",
                        "description": "Ob es ein neuer Patient ist",
                    },
                },
                "required": ["patient_name", "date", "time", "reason"],
            },
        },
    },
    {
        "type": "transferCall",
        "function": {
            "name": "transfer_call",
            "description": "Leitet den Anruf an die Praxis weiter (z.B. für Rezepte, Überweisungen)",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Zielnummer oder Abteilung (z.B. 'praxis', 'labor')",
                        "default": "praxis",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Grund der Weiterleitung",
                    },
                },
                "required": ["destination"],
            },
        },
        "destinations": [
            {
                "type": "number",
                "number": "+498912345678",
                "message": "Ich verbinde Sie jetzt mit der Praxis. Einen Moment bitte.",
            }
        ],
    },
    {
        "type": "function",
        "function": {
            "name": "send_summary",
            "description": "Sendet eine Zusammenfassung des Anrufs an das Praxisteam",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Zusammenfassung des Anrufs",
                    },
                    "caller_name": {
                        "type": "string",
                        "description": "Name des Anrufers",
                    },
                    "action_required": {
                        "type": "boolean",
                        "description": "Ob eine Aktion vom Team erforderlich ist",
                    },
                },
                "required": ["summary"],
            },
        },
    },
]


def get_assistant_config(webhook_url: str) -> dict:
    """Build the full Vapi assistant configuration."""
    return {
        "name": "Lisa - Praxis Dr. Müller",
        "firstMessage": FIRST_MESSAGE,
        "model": {
            **MODEL_CONFIG,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
        },
        "voice": VOICE_CONFIG,
        "serverUrl": webhook_url,
        "maxDurationSeconds": 300,
        "endCallMessage": "Vielen Dank für Ihren Anruf. Auf Wiederhören!",
    }
