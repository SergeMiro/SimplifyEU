"""
Tax and Reporting Assistant Agent.

Responsibilities:
- Build a personalized tax obligation calendar based on business type
- Auto-prepare turnover drafts for declarations
- Anti-fine mode: reminders N days before deadlines
- WhatsApp delivery of deadline alerts with draft data and links
"""

from crewai import Agent
from ..tools.database_tools import (
    get_tax_obligations,
    save_tax_obligation,
    get_business_profile,
    log_agent_execution,
)
from ..tools.calendar_tools import (
    generate_tax_calendar,
    calculate_turnover_for_period,
    check_upcoming_deadlines,
)
from ..tools.notification_tools import (
    send_whatsapp_notification,
    send_email_notification,
    save_in_app_notification,
    get_user_contact_info,
)


def create_tax_assistant() -> Agent:
    """Create the Tax and Reporting Assistant agent."""
    return Agent(
        role="Tax and Reporting Assistant",
        goal=(
            "Ensure the business owner never misses a tax deadline. Build a personalized "
            "calendar of obligations based on their business type (micro-entrepreneur, SARL, "
            "SAS, etc.), prepare draft turnover figures for declarations, and send timely "
            "reminders via WhatsApp with the exact numbers, deadlines, and links to the "
            "relevant government portals (impots.gouv.fr, autoentrepreneur.urssaf.fr)."
        ),
        backstory=(
            "You are a tax compliance assistant specialized in the French tax system. "
            "You know the deadlines for micro-entrepreneur declarations, TVA, IS acomptes, "
            "cotisations sociales, and CFE. You understand the difference between monthly "
            "and quarterly filing, and you know the penalties for late filing (starting at ~60€ "
            "per missed declaration for micro-entrepreneurs). You are NOT an expert-comptable "
            "and never claim to provide official tax advice — you are a 'rappel et compagnon' "
            "who helps the business owner understand what to file, when, and with what numbers. "
            "You communicate in clear, simple French with exact figures and direct links."
        ),
        tools=[
            get_tax_obligations,
            save_tax_obligation,
            get_business_profile,
            generate_tax_calendar,
            calculate_turnover_for_period,
            check_upcoming_deadlines,
            send_whatsapp_notification,
            send_email_notification,
            save_in_app_notification,
            get_user_contact_info,
            log_agent_execution,
        ],
        verbose=True,
        allow_delegation=False,
    )
