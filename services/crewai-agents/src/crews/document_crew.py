"""
Document Crew — triggered when a new document is uploaded.

Tasks:
1. Parse the document and extract key info
2. Match it to an existing transaction
3. Report unlinked documents
"""

from crewai import Crew, Task
from ..agents.document_manager import create_document_manager


class DocumentCrew:
    """Crew for document management and transaction linking."""

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.agent = create_document_manager()

    def create_tasks(self) -> list[Task]:
        match_task = Task(
            description=(
                f"Match uploaded documents to bank transactions for account {self.account_id}. "
                "Steps:\n"
                "1. Fetch all unlinked documents (invoices without a transaction match)\n"
                "2. Fetch recent transactions\n"
                "3. For each unlinked document, try to find a matching transaction by:\n"
                "   - Amount (exact or close match)\n"
                "   - Date (within 3 days)\n"
                "   - Vendor name (fuzzy match)\n"
                "4. Link matched pairs with a confidence score\n"
                "5. Report remaining unlinked documents"
            ),
            expected_output=(
                "A JSON object with:\n"
                "- matched: list of newly linked document-transaction pairs with confidence\n"
                "- unlinked: list of documents still without a match\n"
                "- total_processed: number of documents checked"
            ),
            agent=self.agent,
        )

        notify_task = Task(
            description=(
                f"Notify about document matching results for account {self.account_id}. "
                "1. Save an in-app notification with the matching summary\n"
                "2. If there are unlinked documents, alert the user:\n"
                "   'X documents n'ont pas trouvé de correspondance bancaire. "
                "   Vérifiez dans votre espace SimplifyEU.'\n"
                "3. Log the execution"
            ),
            expected_output=(
                "Confirmation that:\n"
                "- In-app notification saved\n"
                "- Execution logged"
            ),
            agent=self.agent,
        )

        return [match_task, notify_task]

    def build(self) -> Crew:
        return Crew(
            agents=[self.agent],
            tasks=self.create_tasks(),
            verbose=True,
        )

    def run(self) -> str:
        crew = self.build()
        return crew.kickoff()
