# agents/base_agent.py
import os
import logging
from typing import Any, Dict, Optional
from app.connectors.factory import get_connector
from core.error_handler import handle_error
from core.logger import get_logger

logger = get_logger(__name__)

class BaseAgent:
    """
    Base class for all agents.
    Provides:
      - Shared connector handling
      - Diagnostic error handling
      - Retry utilities
    """

    TASK_NAME: str = "base"

    def __init__(self, diagnostic_run: Optional[bool] = True, diagnostic_config: Optional[dict] = None):
        self.diagnostic_run = diagnostic_run
        self.diagnostic_config = diagnostic_config or {}

    def get_connector(self) -> Any:
        """Get connector for this agent (normal or diagnostic mode)."""
        if self.diagnostic_run and self.diagnostic_config.get("type") == "connector_reconfig":
            diag_connector = self.diagnostic_config.get("diagnostic_connector")
            if not diag_connector:
                raise ValueError("Missing 'diagnostic_connector' in diagnostic params.")
            return get_connector(diag_connector)
        return get_connector(self.TASK_NAME)

    def handle_failure(self, error: Exception, retry_callback, agent_args: dict) -> Dict[str, Any]:
        """Handles retry logic using diagnostic mode and handle_error."""
        if not self.diagnostic_run:
            try:
                logger.warning("Retrying in diagnostic mode...")
                return handle_error(
                    error=error,
                    task=self.TASK_NAME,
                    retry_callback=retry_callback,
                    agent_args=agent_args
                )
            except Exception as retry_error:
                logger.critical(f"Retry failed: {retry_error}", exc_info=True)
                return {"status": "fail", "path": None, "error_message": str(retry_error)}

        # Already diagnostic
        return {"status": "fail", "path": None, "error_message": str(error)}
