"""
Operations Coordinator / Chief of Staff Agent.

Responsibilities:
- Weekly briefing aggregating all agent insights
- Priority action items for the coming week
- Single WhatsApp message with a clear summary
- Dashboard link for details
"""

from crewai import Agent
from ..tools.database_tools import (
    get_recent_transactions,
    get_financial_insights,
    get_tax_obligations,
    get_duplicate_pairs,
    get_subscription_analysis,
    log_agent_execution,
)
from ..tools.calendar_tools import check_upcoming_deadlines
from ..tools.document_tools import get_unlinked_documents
from ..tools.notification_tools import (
    send_whatsapp_notification,
    send_email_notification,
    save_in_app_notification,
    get_user_contact_info,
)


def create_operations_coordinator() -> Agent:
    """Create the Operations Coordinator (Chief of Staff) agent."""
    return Agent(
        role="Operations Coordinator — Chief of Staff",
        goal=(
            "Provide the business owner with a concise weekly briefing that summarizes "
            "the most important things they need to know and act on. Aggregate insights "
            "from all other agents (financial, tax, document, client) into a single, "
            "clear summary delivered via WhatsApp every Monday morning. Include: upcoming "
            "deadlines, outstanding issues, financial highlights, and a direct link to "
            "the SimplifyEU dashboard for details."
        ),
        backstory=(
            "You are the Chief of Staff for a French small business owner. Your role is "
            "to synthesize everything that happened during the week and everything that "
            "needs attention in the coming week into one short, actionable message. "
            "Think of yourself as a trusted executive assistant who says: 'Cette semaine, "
            "voici ce qui est important pour vous:' followed by 3-5 bullet points. "
            "No fluff, no jargon — just clear priorities. You always end with "
            "'Tout le reste est en ordre.' when there are no critical issues, or with "
            "specific action items when there are. You deliver this via WhatsApp and "
            "in-app notification."
        ),
        tools=[
            get_recent_transactions,
            get_financial_insights,
            get_tax_obligations,
            get_duplicate_pairs,
            get_subscription_analysis,
            check_upcoming_deadlines,
            get_unlinked_documents,
            send_whatsapp_notification,
            send_email_notification,
            save_in_app_notification,
            get_user_contact_info,
            log_agent_execution,
        ],
        verbose=True,
        allow_delegation=True,
    )
