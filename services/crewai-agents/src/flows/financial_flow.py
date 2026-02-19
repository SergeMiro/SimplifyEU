"""
Financial Flow — event-driven orchestration for the Financial Crew.

Triggers:
- New bank statement uploaded/analyzed
- Manual trigger from dashboard
"""

import logging
from datetime import datetime
from crewai.flow.flow import Flow, start, listen
from pydantic import BaseModel
from ..crews.financial_crew import FinancialCrew

logger = logging.getLogger(__name__)


class FinancialFlowState(BaseModel):
    account_id: str = ""
    trigger: str = ""
    analysis_result: str = ""
    notification_result: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"


class FinancialFlow(Flow[FinancialFlowState]):
    """Flow for financial reconciliation triggered by new bank data."""

    @start()
    def run_analysis(self):
        """Entry point: run the financial crew analysis."""
        logger.info(f"[FinancialFlow] Starting for account {self.state.account_id}")
        self.state.started_at = datetime.utcnow().isoformat()
        self.state.status = "running"

        try:
            crew = FinancialCrew(self.state.account_id)
            result = crew.run()
            self.state.analysis_result = str(result)
            logger.info("[FinancialFlow] Analysis completed")
            return result
        except Exception as e:
            logger.error(f"[FinancialFlow] Analysis failed: {e}")
            self.state.status = "failed"
            raise

    @listen(run_analysis)
    def finalize(self, analysis_output):
        """Finalize the flow after analysis completes."""
        self.state.completed_at = datetime.utcnow().isoformat()
        self.state.status = "completed"
        logger.info(
            f"[FinancialFlow] Completed for account {self.state.account_id}"
        )
        return {
            "account_id": self.state.account_id,
            "status": self.state.status,
            "started_at": self.state.started_at,
            "completed_at": self.state.completed_at,
        }
