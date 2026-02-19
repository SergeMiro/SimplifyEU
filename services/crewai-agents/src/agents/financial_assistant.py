"""
Financial Reconciliation Assistant Agent.

Responsibilities:
- Extended reconciliation: duplicates, anomalies, unknown counterparties
- Transaction tagging (taxes, rent, subscriptions, client income, cash, etc.)
- Auto-insights on account activity (spending trends, late payers, turnover changes)
- WhatsApp/email notifications about important findings
"""

from crewai import Agent
from ..tools.database_tools import (
    get_recent_transactions,
    get_duplicate_pairs,
    get_subscription_analysis,
    get_financial_insights,
    save_financial_insight,
    log_agent_execution,
)
from ..tools.notification_tools import (
    send_whatsapp_notification,
    send_email_notification,
    save_in_app_notification,
    get_user_contact_info,
)


def create_financial_assistant() -> Agent:
    """Create the Financial Reconciliation Assistant agent."""
    return Agent(
        role="Financial Reconciliation Assistant",
        goal=(
            "Analyze bank transactions to find anomalies, duplicates, unusual expenses, "
            "and recurring subscriptions. Tag transactions by category and generate "
            "actionable financial insights for the business owner. Communicate findings "
            "clearly and concisely via WhatsApp and in-app notifications."
        ),
        backstory=(
            "You are a meticulous financial assistant specialized in French small business "
            "accounting. You work for SimplifyEU, a platform that helps entrepreneurs manage "
            "their finances. Your job is to review bank statements and transaction data, "
            "flag anything suspicious or noteworthy, and deliver clear, jargon-free summaries. "
            "You understand European banking formats, French business expenses, and common "
            "subscription patterns. You always communicate in simple, friendly French — "
            "never in accounting jargon. You are not an official accountant (expert-comptable), "
            "but a helpful assistant that ensures nothing falls through the cracks."
        ),
        tools=[
            get_recent_transactions,
            get_duplicate_pairs,
            get_subscription_analysis,
            get_financial_insights,
            save_financial_insight,
            send_whatsapp_notification,
            send_email_notification,
            save_in_app_notification,
            get_user_contact_info,
            log_agent_execution,
        ],
        verbose=True,
        allow_delegation=False,
    )
