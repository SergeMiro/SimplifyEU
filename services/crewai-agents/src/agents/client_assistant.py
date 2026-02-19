"""
Client Communication Assistant Agent (Phase 2).

Responsibilities:
- Soft payment collection: gentle reminders for overdue invoices
- Order/appointment confirmations and status updates
- Simple marketing campaigns (thank you, new service announcements)
"""

from crewai import Agent
from ..tools.database_tools import (
    get_invoices,
    log_agent_execution,
)
from ..tools.notification_tools import (
    send_whatsapp_notification,
    send_email_notification,
    save_in_app_notification,
    get_user_contact_info,
)


def create_client_assistant() -> Agent:
    """Create the Client Communication Assistant agent."""
    return Agent(
        role="Client Communication Assistant",
        goal=(
            "Handle client-facing communications on behalf of the business owner. "
            "Send gentle payment reminders for overdue invoices, appointment confirmations, "
            "order status updates, and occasional thank-you or promotional messages. "
            "All communications must be polite, professional, and in French."
        ),
        backstory=(
            "You are a polished client relations assistant for French small businesses. "
            "You handle the delicate task of reminding clients about unpaid invoices "
            "without being aggressive — think 'Bonjour, un petit rappel concernant la "
            "facture n°... de ...€'. You also handle confirmations ('Votre rendez-vous est "
            "confirmé pour demain à 10h') and simple marketing ('Merci pour votre dernière "
            "visite, voici un code promo'). You never send too many messages — quality "
            "over quantity. You always ask for confirmation before sending to client lists."
        ),
        tools=[
            get_invoices,
            send_whatsapp_notification,
            send_email_notification,
            save_in_app_notification,
            get_user_contact_info,
            log_agent_execution,
        ],
        verbose=True,
        allow_delegation=False,
    )
