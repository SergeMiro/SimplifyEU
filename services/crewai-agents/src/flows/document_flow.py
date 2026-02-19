"""
Document Flow — event-driven orchestration for the Document Crew.

Triggers:
- New document uploaded (invoice, receipt)
- Manual trigger for batch matching
"""

import logging
from datetime import datetime
from crewai.flow.flow import Flow, start, listen
from pydantic import BaseModel
from ..crews.document_crew import DocumentCrew

logger = logging.getLogger(__name__)


class DocumentFlowState(BaseModel):
    account_id: str = ""
    trigger: str = ""
    document_id: str = ""
    match_result: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"


class DocumentFlow(Flow[DocumentFlowState]):
    """Flow for document matching and organization."""

    @start()
    def run_document_matching(self):
        """Entry point: run the document crew."""
        logger.info(f"[DocumentFlow] Starting for account {self.state.account_id}")
        self.state.started_at = datetime.utcnow().isoformat()
        self.state.status = "running"

        try:
            crew = DocumentCrew(self.state.account_id)
            result = crew.run()
            self.state.match_result = str(result)
            logger.info("[DocumentFlow] Document matching completed")
            return result
        except Exception as e:
            logger.error(f"[DocumentFlow] Document matching failed: {e}")
            self.state.status = "failed"
            raise

    @listen(run_document_matching)
    def finalize(self, match_output):
        """Finalize the flow."""
        self.state.completed_at = datetime.utcnow().isoformat()
        self.state.status = "completed"
        logger.info(f"[DocumentFlow] Completed for account {self.state.account_id}")
        return {
            "account_id": self.state.account_id,
            "status": self.state.status,
            "started_at": self.state.started_at,
            "completed_at": self.state.completed_at,
        }
