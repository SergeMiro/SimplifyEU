"""
Tax Flow — event-driven orchestration for the Tax Crew.

Triggers:
- Daily cron check for upcoming deadlines
- Business profile update
- Manual trigger from dashboard
"""

import logging
from datetime import datetime
from crewai.flow.flow import Flow, start, listen
from pydantic import BaseModel
from ..crews.tax_crew import TaxCrew

logger = logging.getLogger(__name__)


class TaxFlowState(BaseModel):
    account_id: str = ""
    trigger: str = ""
    calendar_result: str = ""
    reminder_result: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"


class TaxFlow(Flow[TaxFlowState]):
    """Flow for tax compliance checks and reminders."""

    @start()
    def run_tax_check(self):
        """Entry point: run the tax crew."""
        logger.info(f"[TaxFlow] Starting for account {self.state.account_id}")
        self.state.started_at = datetime.utcnow().isoformat()
        self.state.status = "running"

        try:
            crew = TaxCrew(self.state.account_id)
            result = crew.run()
            self.state.calendar_result = str(result)
            logger.info("[TaxFlow] Tax check completed")
            return result
        except Exception as e:
            logger.error(f"[TaxFlow] Tax check failed: {e}")
            self.state.status = "failed"
            raise

    @listen(run_tax_check)
    def finalize(self, tax_output):
        """Finalize the flow."""
        self.state.completed_at = datetime.utcnow().isoformat()
        self.state.status = "completed"
        logger.info(f"[TaxFlow] Completed for account {self.state.account_id}")
        return {
            "account_id": self.state.account_id,
            "status": self.state.status,
            "started_at": self.state.started_at,
            "completed_at": self.state.completed_at,
        }
