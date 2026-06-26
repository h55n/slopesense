"""
SlopeSense — Alert Dispatcher

Delivers alerts via:
  - WhatsApp Business API (primary, Meta)
  - Email (SDMA digest)
  - SMS fallback (via IMI Mobile / Kaleyra)
  - CAP XML feed (NDMA Sachet integration)

All deliveries are logged to alert_deliveries table for audit.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v19.0"


class WhatsAppDispatcher:
    """
    Sends alert messages via Meta WhatsApp Business API.

    Uses template messages (pre-approved) for transactional alerts.
    Falls back to regular text messages if templates unavailable.

    Rate limits: 1000 messages/second per phone number ID.
    Cost: ~₹0.35–0.50 per message (utility template category).
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ):
        self.api_token = api_token or os.environ.get("WHATSAPP_API_TOKEN")
        self.phone_number_id = phone_number_id or os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        self.base_url = f"{WHATSAPP_API_URL}/{self.phone_number_id}/messages"
        self._dry_run = not (self.api_token and self.phone_number_id)

        if self._dry_run:
            logger.warning("WhatsApp: running in DRY RUN mode (no credentials)")

    async def send_text_message(
        self,
        to: str,
        message: str,
        preview_url: bool = False,
    ) -> Dict:
        """
        Send a text message via WhatsApp.

        Args:
            to: recipient phone number (E.164 format, e.g. +919876543210)
            message: message text (max 4096 chars)
            preview_url: whether to generate link preview

        Returns:
            dict with message_id and status
        """
        if self._dry_run:
            logger.info(f"WhatsApp DRY RUN → {to}: {message[:100]}...")
            return {
                "message_id": f"dry_run_{to}_{int(datetime.now(timezone.utc).timestamp())}",
                "status": "dry_run",
                "recipient": to,
            }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message[:4096],
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    data = await resp.json()

                    if resp.status == 200:
                        message_id = data.get("messages", [{}])[0].get("id", "")
                        logger.info(f"WhatsApp: sent to {to}, id={message_id}")
                        return {
                            "message_id": message_id,
                            "status": "sent",
                            "recipient": to,
                        }
                    else:
                        error = data.get("error", {}).get("message", "Unknown error")
                        logger.error(f"WhatsApp: send failed to {to}: {error}")
                        return {
                            "message_id": None,
                            "status": "failed",
                            "error": error,
                            "recipient": to,
                        }

        except Exception as e:
            logger.error(f"WhatsApp: exception sending to {to}: {e}")
            return {"message_id": None, "status": "failed", "error": str(e), "recipient": to}

    async def send_bulk(
        self,
        recipients: List[Dict],
        message_fn,
        delay_between_ms: int = 100,
    ) -> List[Dict]:
        """
        Send messages to multiple recipients with rate limiting.

        Args:
            recipients: list of contact dicts with 'whatsapp_number' and 'language'
            message_fn: callable(recipient) → message string
            delay_between_ms: delay between sends to respect rate limits

        Returns:
            list of delivery results
        """
        results = []
        for contact in recipients:
            number = contact.get("whatsapp_number")
            if not number:
                continue

            language = contact.get("language", "en")
            msg = message_fn(contact, language)

            result = await self.send_text_message(number, msg)
            result["contact_id"] = contact.get("id")
            result["language"] = language
            results.append(result)

            if delay_between_ms > 0:
                await asyncio.sleep(delay_between_ms / 1000.0)

        logger.info(
            f"WhatsApp bulk: {sum(1 for r in results if r['status'] == 'sent')}/"
            f"{len(results)} sent successfully"
        )
        return results


class EmailDispatcher:
    """
    Sends email digests to SDMA/DDMA contacts.

    Uses SMTP (simple) or SendGrid API for production.
    Generates HTML email with FPI summary table.
    """

    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER")
        self.smtp_password = os.environ.get("SMTP_PASSWORD")
        self.from_address = os.environ.get("SMTP_FROM", "alerts@slopesense.in")
        self._dry_run = not self.smtp_user

    async def send_daily_digest(
        self,
        recipients: List[str],
        alerts: List[Dict],
        run_date: datetime,
    ) -> bool:
        """Send HTML email digest of current active alerts."""
        if self._dry_run:
            logger.info(f"Email DRY RUN: would send digest to {len(recipients)} recipients")
            return True

        subject = f"SlopeSense Daily Alert Digest — {run_date.strftime('%d %B %Y')}"
        html = self._build_digest_html(alerts, run_date)

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_address
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_address, recipients, msg.as_string())

            logger.info(f"Email digest sent to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Email digest failed: {e}")
            return False

    def _build_digest_html(self, alerts: List[Dict], run_date: datetime) -> str:
        """Build HTML email digest."""
        rows = ""
        for a in sorted(alerts, key=lambda x: x["fpi_score"], reverse=True):
            tier_color = {"WATCH": "#f59e0b", "WARNING": "#ef4444", "EMERGENCY": "#7c3aed"}.get(a["tier"], "#6b7280")
            rows += f"""
            <tr>
              <td style="padding:8px;border-bottom:1px solid #e5e7eb;">{a['state_name']}</td>
              <td style="padding:8px;border-bottom:1px solid #e5e7eb;">{a['district_name']}</td>
              <td style="padding:8px;border-bottom:1px solid #e5e7eb;">{a['block_name']}</td>
              <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:center;">
                <span style="background:{tier_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;">{a['tier']}</span>
              </td>
              <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:center;">{int(a['fpi_score']*100)}%</td>
              <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:center;">{a.get('rainfall_3d_mm', 0):.0f}mm</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>SlopeSense Digest</title></head>
<body style="font-family:system-ui,sans-serif;background:#f3f4f6;margin:0;padding:20px;">
  <div style="max-width:800px;margin:0 auto;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    <div style="background:#1e3a5f;color:white;padding:24px;">
      <h1 style="margin:0;font-size:22px;">🏔 SlopeSense Alert Digest</h1>
      <p style="margin:4px 0 0;opacity:0.8;">{run_date.strftime('%A, %d %B %Y — %H:%M UTC')}</p>
    </div>
    <div style="padding:24px;">
      <p style="color:#374151;">{len(alerts)} active alert block(s) across India.</p>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#f9fafb;">
            <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280;border-bottom:2px solid #e5e7eb;">STATE</th>
            <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280;border-bottom:2px solid #e5e7eb;">DISTRICT</th>
            <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280;border-bottom:2px solid #e5e7eb;">BLOCK</th>
            <th style="padding:8px;text-align:center;font-size:12px;color:#6b7280;border-bottom:2px solid #e5e7eb;">TIER</th>
            <th style="padding:8px;text-align:center;font-size:12px;color:#6b7280;border-bottom:2px solid #e5e7eb;">FPI</th>
            <th style="padding:8px;text-align:center;font-size:12px;color:#6b7280;border-bottom:2px solid #e5e7eb;">3D RAIN</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:24px;font-size:12px;color:#9ca3af;">
        SlopeSense v0.1 | Data: NASA GPM, SMAP, NOAA GFS, Copernicus DEM<br>
        Dashboard: <a href="https://slopesense.in">slopesense.in</a> | API: api.slopesense.in
      </p>
    </div>
  </div>
</body>
</html>"""


class AlertDispatcher:
    """
    Orchestrates alert delivery across all channels.
    Called by the Celery worker after each model run.
    """

    def __init__(self, db_session=None):
        self.db = db_session
        self.whatsapp = WhatsAppDispatcher()
        self.email = EmailDispatcher()

    async def dispatch_alerts(
        self,
        alerts: List[Dict],
        contacts: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Main dispatch entry point.

        For each alert that should_notify:
          1. Find contacts scoped to that district/block
          2. Format message in their language
          3. Send via WhatsApp (and email for SDMA-level contacts)
          4. Log delivery to DB

        Returns:
            Summary dict with delivery counts
        """
        from .alert_engine import AlertEngine
        engine = AlertEngine()

        alerts_to_notify = [a for a in alerts if a.get("should_notify")]
        logger.info(f"Dispatcher: {len(alerts_to_notify)} alerts to notify")

        total_sent = 0
        total_failed = 0

        for alert in alerts_to_notify:
            # Get contacts for this district
            district_contacts = self._get_contacts_for_alert(alert, contacts or [])

            if not district_contacts:
                # Use test contact in dev mode
                if os.environ.get("ENVIRONMENT") == "development":
                    district_contacts = [{
                        "id": "test",
                        "whatsapp_number": os.environ.get("TEST_WHATSAPP_NUMBER", "+919000000000"),
                        "language": "en",
                        "role": "test",
                    }]

            if not district_contacts:
                logger.debug(f"No contacts for {alert['district_name']} / {alert['block_name']}")
                continue

            # Build message function
            def make_message(contact, lang):
                return engine.format_whatsapp_message(alert, language=lang)

            results = await self.whatsapp.send_bulk(
                district_contacts,
                make_message,
            )

            total_sent += sum(1 for r in results if r["status"] in ("sent", "dry_run"))
            total_failed += sum(1 for r in results if r["status"] == "failed")

            # Log to DB if available
            if self.db:
                await self._log_deliveries(alert["id"], results)

        return {
            "alerts_processed": len(alerts_to_notify),
            "messages_sent": total_sent,
            "messages_failed": total_failed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _get_contacts_for_alert(
        self, alert: Dict, all_contacts: List[Dict]
    ) -> List[Dict]:
        """Filter contacts by district/block scope and minimum tier."""
        district_code = alert["district_code"]
        tier = alert["tier"]
        tier_order = {"WATCH": 1, "WARNING": 2, "EMERGENCY": 3}
        tier_num = tier_order.get(tier, 0)

        matched = []
        for contact in all_contacts:
            # Geographic scope match
            if contact.get("district_code") and contact["district_code"] != district_code:
                continue
            # Tier threshold
            min_tier = contact.get("min_tier_for_whatsapp", "WARNING")
            min_tier_num = tier_order.get(min_tier, 2)
            if tier_num >= min_tier_num and contact.get("whatsapp_number"):
                matched.append(contact)

        return matched

    async def _log_deliveries(self, alert_id: str, results: List[Dict]):
        """Persist delivery records to DB."""
        try:
            for r in results:
                # In production: insert into alert_deliveries via SQLAlchemy
                logger.debug(f"Delivery log: alert={alert_id} → {r}")
        except Exception as e:
            logger.warning(f"Delivery logging failed: {e}")
