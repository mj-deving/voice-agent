"""Vapi Agent configuration — loads praxis config from YAML."""

from datetime import datetime
from pathlib import Path

import yaml

from src.holidays import is_holiday, is_outside_hours

CONFIGS_DIR = Path(__file__).parent.parent / "configs"
DEFAULT_CONFIG = CONFIGS_DIR / "examples" / "praxis_mueller.yaml"


def load_praxis_config(config_path: str | Path | None = None) -> dict:
    """Load a praxis configuration from YAML.

    Falls back to praxis_mueller.yaml if no path given.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if not path.exists():
        raise FileNotFoundError(f"Praxis config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


VOICE_CONFIG = {
    "provider": "11labs",
    "voiceId": "21m00Tcm4TlvDq8ikWAM",
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


def build_system_prompt(config: dict) -> str:
    """Generate the system prompt from a praxis config."""
    services_list = ", ".join(config["services"])
    return (
        f"Du bist Lisa, die KI-Assistentin der {config['praxis_name']}, "
        f"{config['arzt_name']}, {config['arzt_titel']}.\n\n"
        f"Deine Aufgaben:\n"
        f"1. Begrüße den Anrufer freundlich und frage nach dem Anliegen\n"
        f"2. Finde heraus: Neuer oder bestehender Patient?\n"
        f"3. Erfasse: Name, Geburtsdatum (bei neuen Patienten), Anliegen/Beschwerden\n"
        f"4. Bei Terminwunsch: Schlage verfügbare Zeiten vor und buche mit dem book_appointment Tool\n"
        f"5. Bei Notfall (Brustschmerzen, Atemnot, starke Blutung, Bewusstlosigkeit): "
        f"Sofort empfehlen den Notruf {config['notfall_nummer']} anzurufen. "
        f"Keinen Termin buchen, keine Weiterleitung.\n"
        f"6. Bei Rezepten/Überweisungen: An die Praxis weiterleiten mit transfer_call\n"
        f"7. Bei allgemeinen Fragen (Öffnungszeiten, Adresse): Direkt beantworten\n"
        f"8. Fasse am Ende zusammen was vereinbart wurde\n\n"
        f"Wichtige Informationen:\n"
        f"- Öffnungszeiten: {config['oeffnungszeiten']}\n"
        f"- Adresse: {config['adresse']}\n"
        f"- Telefon Praxis: {config['telefon']}\n"
        f"- Notfallnummer: {config['notfall_nummer']}\n"
        f"- Leistungen: {services_list}\n\n"
        f"Ton: Freundlich, professionell, empathisch. Sprich immer Deutsch.\n"
        f"Halte dich kurz und präzise. Frage immer nur eine Sache auf einmal."
    )


def build_first_message(config: dict, now: datetime | None = None) -> str:
    """Generate the first message based on holiday/hours status.

    Returns holiday greeting, outside-hours greeting, or normal greeting.
    """
    if now is None:
        now = datetime.now()

    holiday, holiday_name = is_holiday(now.date())
    if holiday:
        return (
            f"{config['praxis_name']}, hier spricht Lisa, die digitale Assistentin. "
            f"Die Praxis ist heute wegen {holiday_name} geschlossen. "
            f"In Notfällen rufen Sie bitte die {config['notfall_nummer']} an. "
            f"Kann ich Ihnen anderweitig helfen?"
        )

    if is_outside_hours(now):
        return (
            f"{config['praxis_name']}, hier spricht Lisa, die digitale Assistentin. "
            f"Die Praxis ist derzeit geschlossen. "
            f"Unsere Öffnungszeiten sind {config['oeffnungszeiten']}. "
            f"In Notfällen rufen Sie bitte die {config['notfall_nummer']} an. "
            f"Kann ich Ihnen anderweitig helfen?"
        )

    return config["begruessung"]


def build_tool_definitions(config: dict) -> list[dict]:
    """Generate tool definitions with praxis-specific descriptions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": f"Bucht einen Termin für den Patienten in der {config['praxis_name']}",
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
                    "number": config["weiterleitung_nummer"],
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


def get_assistant_config(webhook_url: str, config: dict | None = None) -> dict:
    """Build the full Vapi assistant configuration.

    If no config dict is passed, loads the default praxis_mueller config.
    """
    if config is None:
        config = load_praxis_config()

    system_prompt = build_system_prompt(config)

    return {
        "name": f"Lisa - {config['praxis_name']}",
        "firstMessage": build_first_message(config),
        "model": {
            **MODEL_CONFIG,
            "messages": [{"role": "system", "content": system_prompt}],
        },
        "voice": VOICE_CONFIG,
        "serverUrl": webhook_url,
        "maxDurationSeconds": 300,
        "endCallMessage": config["verabschiedung"],
    }


# Default module-level exports for backward compatibility
_default_config = load_praxis_config()
SYSTEM_PROMPT = build_system_prompt(_default_config)
FIRST_MESSAGE = build_first_message(_default_config)
TOOL_DEFINITIONS = build_tool_definitions(_default_config)
