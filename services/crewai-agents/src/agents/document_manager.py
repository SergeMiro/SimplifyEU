"""
Document Manager / Archivist Agent.

Responsibilities:
- Auto-link documents (invoices, receipts) to bank transactions
- Generate accountant-ready packages for any period
- Search and retrieve documents by query
- Track unlinked documents that need attention
"""

from crewai import Agent
from ..tools.document_tools import (
    link_document_to_transaction,
    search_documents,
    get_unlinked_documents,
    generate_accountant_package,
)
from ..tools.database_tools import (
    get_invoices,
    get_recent_transactions,
    log_agent_execution,
)
from ..tools.notification_tools import (
    save_in_app_notification,
    get_user_contact_info,
)


def create_document_manager() -> Agent:
    """Create the Document Manager agent."""
    return Agent(
        role="Document Manager and Archivist",
        goal=(
            "Keep all financial documents organized and linked to their corresponding "
            "bank transactions. Ensure that at any moment, the business owner can produce "
            "a complete document package for their accountant or for a tax inspection. "
            "Proactively identify unlinked documents and suggest matches."
        ),
        backstory=(
            "You are a meticulous document management assistant for French small businesses. "
            "You understand that French law requires businesses to keep receipts and invoices "
            "linked to their accounting records. You know how to match a document to a "
            "transaction by comparing amounts, dates, and vendor names. You can generate "
            "organized packages for the expert-comptable with a summary, transaction list, "
            "and linked documents. You communicate findings in simple French."
        ),
        tools=[
            link_document_to_transaction,
            search_documents,
            get_unlinked_documents,
            generate_accountant_package,
            get_invoices,
            get_recent_transactions,
            save_in_app_notification,
            get_user_contact_info,
            log_agent_execution,
        ],
        verbose=True,
        allow_delegation=False,
    )
