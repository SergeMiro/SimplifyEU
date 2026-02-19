"""
Tax Crew — triggered on schedule (daily check) or when business profile changes.

Tasks:
1. Generate/refresh the tax obligation calendar
2. Check upcoming deadlines
3. Prepare turnover draft for upcoming declarations
4. Send anti-fine reminders
"""

from crewai import Crew, Task
from ..agents.tax_assistant import create_tax_assistant


class TaxCrew:
    """Crew for tax compliance and deadline management."""

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.agent = create_tax_assistant()

    def create_tasks(self) -> list[Task]:
        calendar_task = Task(
            description=(
                f"Build or refresh the tax obligation calendar for account {self.account_id}. "
                "Steps:\n"
                "1. Get the business profile (type, tax regime, declaration frequency, TVA status)\n"
                "2. Generate the full tax calendar for the current year\n"
                "3. Save each obligation to the database if not already present\n"
                "4. Return the complete calendar"
            ),
            expected_output=(
                "A JSON object with the complete tax calendar:\n"
                "- obligations: list of obligation objects with type, title, deadline, URL\n"
                "- business_type and tax_regime used\n"
                "- total obligation count"
            ),
            agent=self.agent,
        )

        deadline_check_task = Task(
            description=(
                f"Check for upcoming tax deadlines for account {self.account_id}. "
                "Steps:\n"
                "1. Check all obligations due within the next 14 days\n"
                "2. For each upcoming deadline:\n"
                "   - Calculate days remaining\n"
                "   - If within 5 days: prepare turnover draft using bank/invoice data\n"
                "   - Mark as 'reminded' in the database\n"
                "3. Identify any overdue obligations"
            ),
            expected_output=(
                "A JSON object with:\n"
                "- upcoming: list of upcoming obligations with days_remaining\n"
                "- overdue: list of overdue obligations\n"
                "- drafts: list of prepared turnover drafts with figures"
            ),
            agent=self.agent,
        )

        notify_task = Task(
            description=(
                f"Send tax deadline reminders for account {self.account_id}. "
                "For each upcoming deadline (within 5 days or overdue):\n"
                "1. Get user contact info and preferences\n"
                "2. Compose a WhatsApp message in simple French:\n"
                "   - Deadline name and date\n"
                "   - Draft figures if available (e.g., 'CA estimé: X€')\n"
                "   - Direct link to the government portal\n"
                "   - Warning about penalties if applicable\n"
                "3. Send via WhatsApp if enabled, always save in-app notification\n"
                "4. Log execution\n\n"
                "Example message:\n"
                "'📋 Rappel fiscal — Déclaration CA T1\n"
                "Date limite: 30 avril\n"
                "CA estimé: 12 450€\n"
                "→ Déclarer: autoentrepreneur.urssaf.fr\n"
                "⚠️ Amende ~60€ en cas de retard'"
            ),
            expected_output=(
                "Confirmation of notifications sent with details:\n"
                "- Number of reminders sent\n"
                "- Channels used (WhatsApp, email, in-app)\n"
                "- Execution logged"
            ),
            agent=self.agent,
        )

        return [calendar_task, deadline_check_task, notify_task]

    def build(self) -> Crew:
        return Crew(
            agents=[self.agent],
            tasks=self.create_tasks(),
            verbose=True,
        )

    def run(self) -> str:
        crew = self.build()
        return crew.kickoff()
