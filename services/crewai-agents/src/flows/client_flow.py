"""
Client Communication Flow — event-driven orchestration for the Client Crew.

Triggers:
- Invoice status change (overdue detection)
- Scheduled check for payment follow-ups
"""

import logging
from datetime import datetime
from crewai.flow.flow import Flow, start, listen
from pydantic import BaseModel
from ..crews.client_crew import ClientCrew

logger = logging.getLogger(__name__)


class ClientFlowState(BaseModel):
    account_id: str = ""
    trigger: str = ""
    overdue_result: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"


class ClientFlow(Flow[ClientFlowState]):
    """Flow for client communications and soft collection."""

    @start()
    def run_client_check(self):
        """Entry point: run the client crew."""
        logger.info(f"[ClientFlow] Starting for account {self.state.account_id}")
        self.state.started_at = datetime.utcnow().isoformat()
        self.state.status = "running"

        try:
            crew = ClientCrew(self.state.account_id)
            result = crew.run()
            self.state.overdue_result = str(result)
            logger.info("[ClientFlow] Client check completed")
            return result
        except Exception as e:
            logger.error(f"[ClientFlow] Client check failed: {e}")
            self.state.status = "failed"
            raise

    @listen(run_client_check)
    def finalize(self, client_output):
        """Finalize the flow."""
        self.state.completed_at = datetime.utcnow().isoformat()
        self.state.status = "completed"
        logger.info(f"[ClientFlow] Completed for account {self.state.account_id}")
        return {
            "account_id": self.state.account_id,
            "status": self.state.status,
            "started_at": self.state.started_at,
            "completed_at": self.state.completed_at,
        }
