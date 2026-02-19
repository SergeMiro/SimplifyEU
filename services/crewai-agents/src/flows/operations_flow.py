"""
Operations / Weekly Briefing Flow — cron-triggered (Monday morning).

Triggers:
- Weekly cron schedule
- Manual trigger from dashboard
"""

import logging
from datetime import datetime
from crewai.flow.flow import Flow, start, listen
from pydantic import BaseModel
from ..crews.operations_crew import OperationsCrew

logger = logging.getLogger(__name__)


class OperationsFlowState(BaseModel):
    account_id: str = ""
    trigger: str = ""
    briefing_result: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"


class OperationsFlow(Flow[OperationsFlowState]):
    """Flow for weekly operational briefing."""

    @start()
    def run_weekly_briefing(self):
        """Entry point: run the operations crew."""
        logger.info(f"[OperationsFlow] Starting for account {self.state.account_id}")
        self.state.started_at = datetime.utcnow().isoformat()
        self.state.status = "running"

        try:
            crew = OperationsCrew(self.state.account_id)
            result = crew.run()
            self.state.briefing_result = str(result)
            logger.info("[OperationsFlow] Weekly briefing completed")
            return result
        except Exception as e:
            logger.error(f"[OperationsFlow] Briefing failed: {e}")
            self.state.status = "failed"
            raise

    @listen(run_weekly_briefing)
    def finalize(self, briefing_output):
        """Finalize the flow."""
        self.state.completed_at = datetime.utcnow().isoformat()
        self.state.status = "completed"
        logger.info(
            f"[OperationsFlow] Completed for account {self.state.account_id}"
        )
        return {
            "account_id": self.state.account_id,
            "status": self.state.status,
            "started_at": self.state.started_at,
            "completed_at": self.state.completed_at,
        }
