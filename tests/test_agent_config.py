"""Tests for Vapi agent configuration — Praxis Dr. Müller."""

from src.agent_config import (
    FIRST_MESSAGE,
    MODEL_CONFIG,
    SYSTEM_PROMPT,
    TOOL_DEFINITIONS,
    VOICE_CONFIG,
    get_assistant_config,
)


# --- System Prompt: Lisa persona ---

class TestSystemPromptPersona:
    def test_system_prompt_names_lisa(self):
        assert "Lisa" in SYSTEM_PROMPT

    def test_system_prompt_names_dr_mueller(self):
        assert "Dr. Sarah Müller" in SYSTEM_PROMPT or "Dr. Müller" in SYSTEM_PROMPT

    def test_system_prompt_specifies_allgemeinmedizin(self):
        assert "Allgemeinmedizin" in SYSTEM_PROMPT

    def test_system_prompt_specifies_german_language(self):
        assert "Deutsch" in SYSTEM_PROMPT


# --- System Prompt: Emergency 112 ---

class TestSystemPromptEmergency:
    def test_system_prompt_mentions_112(self):
        assert "112" in SYSTEM_PROMPT

    def test_system_prompt_mentions_brustschmerzen(self):
        assert "Brustschmerzen" in SYSTEM_PROMPT

    def test_system_prompt_mentions_atemnot(self):
        assert "Atemnot" in SYSTEM_PROMPT

    def test_system_prompt_mentions_blutung(self):
        assert "Blutung" in SYSTEM_PROMPT


# --- System Prompt: Opening hours ---

class TestSystemPromptOpeningHours:
    def test_system_prompt_contains_morning_hours(self):
        assert "8:00-12:00" in SYSTEM_PROMPT

    def test_system_prompt_contains_afternoon_hours(self):
        assert "14:00-18:00" in SYSTEM_PROMPT

    def test_system_prompt_contains_weekdays(self):
        assert "Mo-Fr" in SYSTEM_PROMPT


# --- System Prompt: Address ---

class TestSystemPromptAddress:
    def test_system_prompt_contains_street(self):
        assert "Marienplatz 5" in SYSTEM_PROMPT

    def test_system_prompt_contains_plz_city(self):
        assert "80331 München" in SYSTEM_PROMPT


# --- Voice config ---

class TestVoiceConfig:
    def test_voice_provider_is_elevenlabs(self):
        assert VOICE_CONFIG["provider"] == "11labs"

    def test_voice_language_is_german(self):
        assert VOICE_CONFIG["language"] == "de"

    def test_voice_has_voice_id(self):
        assert "voiceId" in VOICE_CONFIG
        assert len(VOICE_CONFIG["voiceId"]) > 0


# --- Model config ---

class TestModelConfig:
    def test_model_provider_is_anthropic(self):
        assert MODEL_CONFIG["provider"] == "anthropic"

    def test_model_is_claude_sonnet(self):
        assert "claude" in MODEL_CONFIG["model"]
        assert "sonnet" in MODEL_CONFIG["model"]

    def test_model_temperature_is_low(self):
        assert MODEL_CONFIG["temperature"] <= 0.5


# --- Tool definitions ---

class TestToolDefinitions:
    def test_three_tools_defined(self):
        assert len(TOOL_DEFINITIONS) == 3

    def test_all_tools_are_function_type(self):
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"


class TestBookAppointmentTool:
    def _get_tool(self):
        return next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "book_appointment")

    def test_book_appointment_exists(self):
        tool = self._get_tool()
        assert tool is not None

    def test_book_appointment_has_patient_name_param(self):
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "patient_name" in props

    def test_book_appointment_has_date_param(self):
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "date" in props

    def test_book_appointment_has_time_param(self):
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "time" in props

    def test_book_appointment_has_reason_param(self):
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "reason" in props

    def test_book_appointment_required_fields(self):
        tool = self._get_tool()
        required = tool["function"]["parameters"]["required"]
        assert "patient_name" in required
        assert "date" in required
        assert "time" in required
        assert "reason" in required


class TestTransferCallTool:
    def _get_tool(self):
        return next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "transfer_call")

    def test_transfer_call_exists(self):
        assert self._get_tool() is not None

    def test_transfer_call_has_destination_param(self):
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "destination" in props

    def test_transfer_call_destination_is_required(self):
        tool = self._get_tool()
        assert "destination" in tool["function"]["parameters"]["required"]


class TestSendSummaryTool:
    def _get_tool(self):
        return next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "send_summary")

    def test_send_summary_exists(self):
        assert self._get_tool() is not None

    def test_send_summary_has_summary_param(self):
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "summary" in props

    def test_send_summary_has_caller_name_param(self):
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "caller_name" in props

    def test_send_summary_has_action_required_param(self):
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "action_required" in props

    def test_send_summary_summary_is_required(self):
        tool = self._get_tool()
        assert "summary" in tool["function"]["parameters"]["required"]


# --- get_assistant_config ---

class TestGetAssistantConfig:
    def test_config_contains_name(self):
        config = get_assistant_config("https://example.com")
        assert "Lisa" in config["name"]

    def test_config_contains_first_message(self):
        config = get_assistant_config("https://example.com")
        assert config["firstMessage"] == FIRST_MESSAGE

    def test_config_contains_server_url(self):
        config = get_assistant_config("https://test.ngrok.io")
        assert config["serverUrl"] == "https://test.ngrok.io"

    def test_config_model_has_system_message(self):
        config = get_assistant_config("https://example.com")
        messages = config["model"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT

    def test_config_voice_matches_voice_config(self):
        config = get_assistant_config("https://example.com")
        assert config["voice"] == VOICE_CONFIG

    def test_config_has_max_duration(self):
        config = get_assistant_config("https://example.com")
        assert config["maxDurationSeconds"] == 300

    def test_config_has_end_call_message_in_german(self):
        config = get_assistant_config("https://example.com")
        assert "Wiederhören" in config["endCallMessage"]
