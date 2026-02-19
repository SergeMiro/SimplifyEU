"""
Financial Crew — triggered when a new bank statement is uploaded or analyzed.

Tasks:
1. Analyze transactions for anomalies and patterns
2. Tag transactions by category
3. Generate financial insights
4. Notify the user of findings
"""

from crewai import Crew, Task
from ..agents.financial_assistant import create_financial_assistant


class FinancialCrew:
    """Crew for financial reconciliation and analysis."""

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.agent = create_financial_assistant()

    def create_tasks(self) -> list[Task]:
        analyze_task = Task(
            description=(
                f"Analyze recent bank transactions for account {self.account_id}. "
                "Perform the following:\n"
                "1. Fetch recent transactions (last 30 days)\n"
                "2. Check for pending duplicate invoice pairs\n"
                "3. Review subscription analysis results\n"
                "4. Identify anomalies: unusually large charges, new unknown vendors, "
                "sudden changes in spending patterns\n"
                "5. Categorize transactions into tags: taxes, rent/loyer, subscriptions, "
                "client income, cash, professional expenses, etc.\n"
                "6. Save all findings as financial insights in the database\n"
                "7. Prepare a concise summary in simple French"
            ),
            expected_output=(
                "A JSON object with keys:\n"
                "- anomalies: list of detected anomalies with severity\n"
                "- tags: dict mapping transaction categories to count and total\n"
                "- insights: list of generated insights\n"
                "- summary_fr: a 3-5 sentence summary in simple French"
            ),
            agent=self.agent,
        )

        notify_task = Task(
            description=(
                f"Send notifications about financial findings for account {self.account_id}. "
                "1. Get the user's notification preferences and contact info\n"
                "2. If WhatsApp is enabled, send a short message with key findings:\n"
                "   - Number of anomalies found\n"
                "   - Monthly spending trend (up/down/stable)\n"
                "   - Any urgent items needing attention\n"
                "3. Always save an in-app notification with the full summary\n"
                "4. Log this execution in the agent execution log"
            ),
            expected_output=(
                "Confirmation that notifications were sent/saved, including:\n"
                "- WhatsApp sent: yes/no\n"
                "- In-app notification saved: yes/no\n"
                "- Execution logged: yes/no"
            ),
            agent=self.agent,
        )

        return [analyze_task, notify_task]

    def build(self) -> Crew:
        return Crew(
            agents=[self.agent],
            tasks=self.create_tasks(),
            verbose=True,
        )

    def run(self) -> str:
        crew = self.build()
        return crew.kickoff()
