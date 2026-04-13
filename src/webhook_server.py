"""FastAPI webhook server for Vapi tool calls."""

import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.availability import book_slot, get_next_available, is_slot_available
from src.call_logger import log_call_event
from src.notifications import send_notification
from src.webhook_auth import HmacAuthMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title="Vapi Webhook Server - Praxis Dr. Müller")
app.add_middleware(HmacAuthMiddleware)

PRAXIS_PHONE = os.environ.get("PRAXIS_PHONE_NUMBER", "089-12345678")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/vapi/webhook")
async def vapi_webhook(request: Request):
    """Handle incoming Vapi webhook requests (tool calls and status updates)."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    message_type = payload.get("message", {}).get("type", "")

    if message_type == "function-call":
        return await _handle_function_call(payload)
    elif message_type == "transfer-destination-request":
        return await _handle_transfer_destination(payload)
    elif message_type == "end-of-call-report":
        return await _handle_end_of_call(payload)
    elif message_type == "status-update":
        return JSONResponse(content={"status": "received"})
    else:
        return JSONResponse(content={"status": "ignored", "type": message_type})


FUNCTION_HANDLERS: dict = {}  # populated after handler definitions


async def _handle_function_call(payload: dict) -> JSONResponse:
    """Route function calls to the appropriate handler."""
    message = payload.get("message", {})
    function_call = message.get("functionCall", {})
    function_name = function_call.get("name", "")
    parameters = function_call.get("parameters", {})

    handler = FUNCTION_HANDLERS.get(function_name)
    if not handler:
        raise HTTPException(
            status_code=400, detail=f"Unknown function: {function_name}"
        )

    result = await handler(parameters)
    return JSONResponse(content={"result": result})


async def _handle_book_appointment(params: dict) -> str:
    """Handle appointment booking requests with availability checking."""
    patient_name = params.get("patient_name", "Unbekannt")
    date = params.get("date", "")
    time = params.get("time", "")
    reason = params.get("reason", "")
    is_new = params.get("is_new_patient", False)

    log_call_event(
        event_type="tool_call",
        caller_name=patient_name,
        action="book_appointment",
        details={"date": date, "time": time, "reason": reason, "is_new_patient": is_new},
    )

    if is_slot_available(date, time):
        book_slot(date, time, patient_name)
        patient_type = "neuer Patient" if is_new else "Patient"
        return (
            f"Termin erfolgreich gebucht: {patient_type} {patient_name} "
            f"am {date} um {time} Uhr. Grund: {reason}. "
            f"Bitte bestätigen Sie dem Anrufer den Termin."
        )

    # Slot unavailable — suggest alternatives
    alternatives = get_next_available(date, time, count=3)
    if alternatives:
        alt_text = ", ".join(
            f"{a['date']} um {a['time']} Uhr" for a in alternatives
        )
        return (
            f"Der Termin am {date} um {time} Uhr ist leider nicht verfügbar. "
            f"Folgende Alternativen sind frei: {alt_text}. "
            f"Bitte fragen Sie den Anrufer, welcher Termin passt."
        )
    return (
        f"Der Termin am {date} um {time} Uhr ist leider nicht verfügbar. "
        f"Derzeit sind keine freien Termine vorhanden. "
        f"Bitte bitten Sie den Anrufer, es später erneut zu versuchen."
    )


async def _handle_transfer_call(params: dict) -> str:
    """Handle call transfer requests."""
    destination = params.get("destination", "praxis")
    reason = params.get("reason", "")

    log_call_event(
        event_type="tool_call",
        action="transfer_call",
        details={"destination": destination, "reason": reason},
    )

    return (
        f"Anruf wird an {destination} weitergeleitet. "
        f"Grund: {reason}. Bitte informieren Sie den Anrufer über die Weiterleitung."
    )


async def _handle_send_summary(params: dict) -> str:
    """Handle call summary sending."""
    summary = params.get("summary", "")
    caller_name = params.get("caller_name", "Unbekannt")
    action_required = params.get("action_required", False)

    log_call_event(
        event_type="tool_call",
        caller_name=caller_name,
        action="send_summary",
        details={
            "summary": summary,
            "action_required": action_required,
        },
    )

    result = await asyncio.to_thread(send_notification, summary, caller_name, action_required)
    if not result.get("email") and not result.get("webhook"):
        logger.warning("No notification channels delivered for call from %s", caller_name)

    action_text = " Aktion erforderlich." if action_required else ""
    return f"Zusammenfassung gesendet.{action_text}"


async def _handle_transfer_destination(payload: dict) -> JSONResponse:
    """Handle transfer-destination-request from Vapi.

    Returns the phone number to transfer the call to.
    """
    message = payload.get("message", {})
    destination = message.get("destination", "praxis")

    log_call_event(
        event_type="transfer_destination",
        action="transfer_call",
        details={"destination": destination},
    )

    return JSONResponse(content={
        "destination": {
            "type": "number",
            "number": PRAXIS_PHONE,
            "message": "Ich verbinde Sie jetzt mit der Praxis. Einen Moment bitte.",
        }
    })


async def _handle_end_of_call(payload: dict) -> JSONResponse:
    """Log end-of-call report."""
    message = payload.get("message", {})

    log_call_event(
        event_type="end_of_call",
        details={
            "duration": message.get("durationSeconds"),
            "ended_reason": message.get("endedReason"),
            "summary": message.get("summary"),
        },
    )

    return JSONResponse(content={"status": "logged"})


# Register handlers after definition
FUNCTION_HANDLERS.update({
    "book_appointment": _handle_book_appointment,
    "transfer_call": _handle_transfer_call,
    "send_summary": _handle_send_summary,
})
