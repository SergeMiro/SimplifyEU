"""
Operations / Chief of Staff Crew — triggered weekly (cron: Monday morning).

Tasks:
1. Aggregate data from all domains
2. Build a concise weekly briefing
3. Deliver via WhatsApp and in-app
"""

from crewai import Crew, Task
from ..agents.operations_coordinator import create_operations_coordinator


class OperationsCrew:
    """Crew for weekly operational briefing."""

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.agent = create_operations_coordinator()

    def create_tasks(self) -> list[Task]:
        gather_task = Task(
            description=(
                f"Gather all relevant data for the weekly briefing of account {self.account_id}. "
                "Collect:\n"
                "1. Financial insights from the past 7 days (anomalies, trends)\n"
                "2. Upcoming tax deadlines (next 14 days)\n"
                "3. Pending duplicate invoice pairs\n"
                "4. Unlinked documents count\n"
                "5. Subscription analysis highlights\n"
                "6. Any overdue client payments\n"
                "Aggregate all data into a structured overview."
            ),
            expected_output=(
                "A JSON object with sections:\n"
                "- financial: key financial insights and anomalies\n"
                "- tax: upcoming deadlines and overdue items\n"
                "- documents: unlinked document count\n"
                "- clients: overdue payment summary\n"
                "- subscriptions: notable subscription findings"
            ),
            agent=self.agent,
        )

        briefing_task = Task(
            description=(
                f"Compose the weekly briefing message for account {self.account_id}. "
                "Format:\n"
                "1. Start with: 'Cette semaine, voici ce qui est important pour vous :'\n"
                "2. List 3-5 priority items as bullet points, e.g.:\n"
                "   – Déclaration CA à déposer avant vendredi (CA estimé : X€)\n"
                "   – 2 clients en retard de paiement > 10 jours\n"
                "   – Dépenses abonnements en hausse de 30%\n"
                "3. End with: 'Tout le reste est en ordre.' OR specific action items\n"
                "4. Add: 'Détails → [link to SimplifyEU dashboard]'\n"
                "5. Keep it under 500 characters for WhatsApp readability"
            ),
            expected_output=(
                "The formatted weekly briefing message in French, "
                "ready for WhatsApp delivery (under 500 characters)."
            ),
            agent=self.agent,
        )

        deliver_task = Task(
            description=(
                f"Deliver the weekly briefing for account {self.account_id}. "
                "1. Get user contact info and preferences\n"
                "2. Send the briefing via WhatsApp if enabled\n"
                "3. Send via email with a nicely formatted HTML version\n"
                "4. Always save as in-app notification\n"
                "5. Log the execution"
            ),
            expected_output=(
                "Confirmation:\n"
                "- WhatsApp sent: yes/no\n"
                "- Email sent: yes/no\n"
                "- In-app saved: yes\n"
                "- Execution logged"
            ),
            agent=self.agent,
        )

        return [gather_task, briefing_task, deliver_task]

    def build(self) -> Crew:
        return Crew(
            agents=[self.agent],
            tasks=self.create_tasks(),
            verbose=True,
        )

    def run(self) -> str:
        crew = self.build()
        return crew.kickoff()
