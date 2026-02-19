"""
Client Communication Crew — triggered by invoice status changes or scheduled campaigns.

Tasks:
1. Check for overdue invoices
2. Send gentle payment reminders
3. Handle appointment confirmations
"""

from crewai import Crew, Task
from ..agents.client_assistant import create_client_assistant


class ClientCrew:
    """Crew for client-facing communications."""

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.agent = create_client_assistant()

    def create_tasks(self) -> list[Task]:
        check_overdue_task = Task(
            description=(
                f"Check for overdue invoices for account {self.account_id}. "
                "Steps:\n"
                "1. Fetch all invoices with 'pending' status\n"
                "2. Identify invoices past their due date\n"
                "3. Group by client/vendor\n"
                "4. Prepare gentle reminder messages in French for each overdue invoice\n"
                "5. Format: 'Bonjour, un petit rappel concernant la facture n°[NUMBER] "
                "de [AMOUNT]€, datée du [DATE]. Merci de votre attention.'\n"
                "6. Save reminders as in-app notifications for user approval before sending"
            ),
            expected_output=(
                "A JSON object with:\n"
                "- overdue_invoices: list of overdue invoices with days overdue\n"
                "- prepared_reminders: list of draft reminder messages\n"
                "- total_overdue_amount: sum of all overdue amounts"
            ),
            agent=self.agent,
        )

        notify_owner_task = Task(
            description=(
                f"Notify the business owner about overdue invoices for account {self.account_id}. "
                "1. Get user contact preferences\n"
                "2. Send a summary to the owner (NOT to the clients):\n"
                "   'Vous avez X factures en retard pour un total de Y€. "
                "   Des rappels sont prêts à envoyer dans votre espace SimplifyEU.'\n"
                "3. The owner must approve before any message goes to clients\n"
                "4. Log execution"
            ),
            expected_output=(
                "Confirmation:\n"
                "- Owner notified: yes/no\n"
                "- Reminders queued for approval: count\n"
                "- Execution logged"
            ),
            agent=self.agent,
        )

        return [check_overdue_task, notify_owner_task]

    def build(self) -> Crew:
        return Crew(
            agents=[self.agent],
            tasks=self.create_tasks(),
            verbose=True,
        )

    def run(self) -> str:
        crew = self.build()
        return crew.kickoff()
