"""HMAC signature verification for Vapi webhooks."""

import hashlib
import hmac
import os
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

BYPASS_PATHS = {"/health"}


class HmacAuthMiddleware(BaseHTTPMiddleware):
    """Verify Vapi webhook signatures using HMAC-SHA256.

    Disabled when VAPI_WEBHOOK_SECRET is not set.
    """

    async def dispatch(self, request: Request, call_next):
        secret = os.environ.get("VAPI_WEBHOOK_SECRET")

        if not secret:
            return await call_next(request)

        if request.url.path in BYPASS_PATHS:
            return await call_next(request)

        if request.method != "POST":
            return await call_next(request)

        signature = request.headers.get("x-vapi-signature", "")
        if not signature:
            logger.warning("Missing x-vapi-signature header")
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing signature"},
            )

        body = await request.body()
        expected = hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            logger.warning("Invalid webhook signature")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid signature"},
            )

        return await call_next(request)
