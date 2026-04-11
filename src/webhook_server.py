"""FastAPI webhook server for Vapi tool calls."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.call_logger import log_call_event

app = FastAPI(title="Vapi Webhook Server - Praxis Dr. Müller")


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
    """Handle appointment booking requests."""
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

    patient_type = "neuer Patient" if is_new else "Patient"
    return (
        f"Termin erfolgreich gebucht: {patient_type} {patient_name} "
        f"am {date} um {time} Uhr. Grund: {reason}. "
        f"Bitte bestätigen Sie dem Anrufer den Termin."
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

    action_text = " Aktion erforderlich." if action_required else ""
    return f"Zusammenfassung gesendet.{action_text}"


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
