"""Notification client — Slack and WhatsApp."""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")  # e.g. whatsapp:+14155238886
WHATSAPP_TO = os.getenv("WHATSAPP_TO", "")  # e.g. whatsapp:+1234567890


async def notify_slack(message: str, channel: str = "#ai-reviews") -> bool:
    """Send a message to Slack via incoming webhook."""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not set, skipping Slack notification")
        return False

    payload = {
        "channel": channel,
        "text": message,
        "username": "AI Company Bot",
        "icon_emoji": ":robot_face:",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if r.status_code == 200:
            logger.info("Slack notification sent")
            return True
        logger.error(f"Slack notification failed: {r.status_code} {r.text}")
        return False


async def notify_whatsapp(message: str, to: str = WHATSAPP_TO) -> bool:
    """Send a WhatsApp message via Twilio."""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, to]):
        logger.warning("Twilio credentials not set, skipping WhatsApp notification")
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={"From": TWILIO_WHATSAPP_FROM, "To": to, "Body": message},
            timeout=10,
        )
        if r.status_code in (200, 201):
            logger.info("WhatsApp notification sent")
            return True
        logger.error(f"WhatsApp notification failed: {r.status_code} {r.text}")
        return False


async def notify_all(message: str) -> None:
    """Send notification to all configured channels."""
    import asyncio
    await asyncio.gather(
        notify_slack(message),
        notify_whatsapp(message),
        return_exceptions=True,
    )
