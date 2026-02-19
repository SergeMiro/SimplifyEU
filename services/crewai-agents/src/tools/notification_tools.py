"""
Notification tools for CrewAI agents.
Support WhatsApp (via Twilio), email (via SMTP), and in-app notifications.
"""

import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crewai.tools import tool
from ..config import settings
from ..db.client import supabase

logger = logging.getLogger(__name__)


def _get_twilio_client():
    """Lazy-load Twilio client to avoid import errors when not configured."""
    if not settings.whatsapp_configured:
        return None
    from twilio.rest import Client
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


@tool("Send WhatsApp notification")
def send_whatsapp_notification(phone_number: str, message: str) -> str:
    """
    Send a WhatsApp message to a user via Twilio.
    phone_number: must include country code, e.g., '+33612345678'
    message: the text message to send (keep it short and actionable)
    """
    if not settings.whatsapp_configured:
        logger.warning("WhatsApp not configured, notification logged but not sent")
        return json.dumps({
            "sent": False,
            "reason": "WhatsApp not configured",
            "message_preview": message[:100],
        })

    try:
        client = _get_twilio_client()
        msg = client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
            body=message,
            to=f"whatsapp:{phone_number}",
        )
        logger.info(f"WhatsApp sent to {phone_number[:6]}*** sid={msg.sid}")
        return json.dumps({"sent": True, "sid": msg.sid})
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return json.dumps({"sent": False, "error": str(e)})


@tool("Send email notification")
def send_email_notification(to_email: str, subject: str, body_html: str) -> str:
    """
    Send an email notification to a user.
    to_email: recipient email address
    subject: email subject line
    body_html: email body in HTML format
    """
    if not settings.smtp_configured:
        logger.warning("SMTP not configured, email logged but not sent")
        return json.dumps({
            "sent": False,
            "reason": "SMTP not configured",
            "subject": subject,
        })

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_SENDER_NAME} <{settings.SMTP_SENDER_EMAIL}>"
        msg["To"] = to_email

        # Plain text fallback
        plain_text = body_html.replace("<br>", "\n").replace("</p>", "\n")
        import re
        plain_text = re.sub(r"<[^>]+>", "", plain_text)

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent to {to_email}")
        return json.dumps({"sent": True, "to": to_email})
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return json.dumps({"sent": False, "error": str(e)})


@tool("Save in-app notification")
def save_in_app_notification(
    account_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    action_url: str = "",
    agent_type: str = "",
) -> str:
    """
    Save an in-app notification for the user to see in their SimplifyEU dashboard.
    notification_type: info, warning, action_required, success
    action_url: optional deep link within the app
    """
    try:
        insert_data = {
            "account_id": account_id,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "read": False,
        }
        if action_url:
            insert_data["action_url"] = action_url
        if agent_type:
            insert_data["agent_type"] = agent_type

        res = supabase.table("agent_notifications").insert(insert_data).execute()
        return json.dumps({
            "saved": True,
            "notification_id": res.data[0]["id"] if res.data else None,
        })
    except Exception as e:
        logger.error(f"Error saving notification: {e}")
        return json.dumps({"saved": False, "error": str(e)})


@tool("Get user contact info")
def get_user_contact_info(account_id: str) -> str:
    """
    Fetch the user's notification preferences and contact info (phone, email).
    """
    try:
        res = (
            supabase.table("agent_settings")
            .select("notification_channels, config")
            .eq("account_id", account_id)
            .limit(1)
            .execute()
        )

        profile_res = (
            supabase.table("business_profiles")
            .select("*")
            .eq("account_id", account_id)
            .limit(1)
            .execute()
        )

        notification_channels = []
        config = {}
        if res.data:
            notification_channels = res.data[0].get("notification_channels", [])
            config = res.data[0].get("config", {})

        phone = config.get("whatsapp_phone", None)
        email = config.get("notification_email", None)

        return json.dumps({
            "channels": notification_channels,
            "phone": phone,
            "email": email,
            "profile": profile_res.data[0] if profile_res.data else None,
        })
    except Exception as e:
        logger.error(f"Error fetching contact info: {e}")
        return json.dumps({"error": str(e)})
