"""Webhook routes for WhatsApp delivery status and field feedback."""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import Response

from backend.config import settings

router = APIRouter(prefix="/v1/webhooks", tags=["Webhooks"])

_feedback_events = []


@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
):
    """Verify the WhatsApp webhook subscription challenge."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Invalid webhook verification token")


@router.post("/whatsapp")
async def whatsapp_webhook_receive(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
):
    """Receive WhatsApp message statuses and block officer feedback."""
    body = await request.body()
    _validate_signature(body, x_hub_signature_256)
    payload = await request.json()
    events = _extract_whatsapp_events(payload)
    _feedback_events.extend(events)
    return {"status": "ok", "events_processed": len(events)}


def _validate_signature(body: bytes, signature_header: str | None):
    if not settings.whatsapp_app_secret:
        return
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Missing WhatsApp signature")

    expected = hmac.new(
        settings.whatsapp_app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.split("=", 1)[1]
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=403, detail="Invalid WhatsApp signature")


def _extract_whatsapp_events(payload: Dict[str, Any]) -> list[dict]:
    events = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status in value.get("statuses", []):
                events.append(
                    {
                        "type": "status",
                        "message_id": status.get("id"),
                        "recipient": status.get("recipient_id"),
                        "status": status.get("status"),
                        "received_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            for message in value.get("messages", []):
                text = (message.get("text") or {}).get("body", "").strip()
                event = {
                    "type": "message",
                    "message_id": message.get("id"),
                    "from": message.get("from"),
                    "text": text,
                    "received_at": datetime.now(timezone.utc).isoformat(),
                }
                if text.upper() in {"NO EVENT", "FALSE ALARM", "NOEVENT"}:
                    event["feedback"] = "false_alarm"
                events.append(event)
    return events
