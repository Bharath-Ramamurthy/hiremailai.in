# connectors/diagnostic_tools.py
import os
import time
import logging
from typing import Optional
from app.connectors.factory import get_connector

logger = logging.getLogger(__name__)



URL = "URL"
TOKEN = "TOKEN"
MODEL = "MODEL"


# -----------------------------
# Tool 1: Switch Connector
# -----------------------------
def switch_connector(task: str):
    """
    Switches the connector for the specified task to its alternate connector (e.g., Hugging Face, OpenAI, or HTTP).
    """
    current_connector = os.getenv(f"{task.upper()}_CONNECTOR")
    connector_precedence = os.getenv("CONNECTOR_PRECEDENCE", "")

    precedence_list = [p.strip() for p in connector_precedence.split(",") if p.strip()]
    if not precedence_list:
        raise RuntimeError("CONNECTOR_PRECEDENCE environment variable is not set or empty.")

    if current_connector and current_connector in precedence_list:
        precedence_list.remove(current_connector)

    if not precedence_list:
        raise RuntimeError(
            f"No connectors left in precedence list after removing current connector '{current_connector}'."
        )

    next_connector = precedence_list[0].lower()
    connector = get_connector(task, reload=True, override_type=next_connector)
    logger.info(f"Switched connector for task '{task}' to '{next_connector}'.")
    return connector


# -----------------------------
# Tool 2: Switch Connector Configuration
# -----------------------------
def switch_config(task: str):
    """
    Switches the specified connector to its alternate configuration (URL, model name, and API key)
    for recovery or failover purposes.
    """
    connector = get_connector(
        task,
        reload=True,
        alt_config=True,
        alt_param_allowlist=[URL, TOKEN, MODEL],
    )
    logger.info(f"Switched connector config for task '{task}' to alternate configuration.")
    return connector


# -----------------------------
# Tool 3: Switch Model
# -----------------------------
def switch_model(task: str):
    """
    Switches the model for the task to alternate model (if available).
    """
    connector = get_connector(task, reload=True, alt_config=True, alt_param_allowlist=[MODEL])
    logger.info(f"Switched model for task '{task}' to alternate model.")
    return connector


# -----------------------------
# Tool 4: Switch Token
# -----------------------------
def switch_token(task: str):
    """
    Refreshes or switches the API token for the task.
    """
    connector = get_connector(task, reload=True, alt_config=True, alt_param_allowlist=[TOKEN])
    logger.info(f"Switched token for task '{task}' to alternate token.")
    return connector


# -----------------------------
# Tool 5: Switch URL
# -----------------------------
def switch_url(task: str):
    """
    Switches the API URL for the task connector.
    """
    connector = get_connector(task, reload=True, alt_config=True, alt_param_allowlist=[URL])
    logger.info(f"Switched API URL for task '{task}' to alternate URL.")
    return connector


# -----------------------------
# Tool 6: Retry After Delay
# -----------------------------
def retry_after_delay(delay: Optional[int] = None):
    """
    Retries a function after a delay.
    """
    if delay is None:
        delay = int(os.getenv("DIAGNOSTIC_TOOL_DELAY_IN_SECS", 5))

    logger.info(f"Retrying operation after {delay} seconds...")
    time.sleep(delay)
    return


# -----------------------------
# Tool Registration for LangChain
# -----------------------------
from langchain.agents import Tool

LANGCHAIN_TOOLS = [
    Tool(
        name="FailoverSwitchConnector",
        func=switch_connector,
        description="Switch to a different connector/provider (e.g., HuggingFace ↔ OpenAI ↔ HTTP).",
    ),
    Tool(
        name="FailoverSwitchConfig",
        func=switch_config,
        description="Switch connector configuration (URL, model name, API key) within the same provider.",
    ),
    Tool(
        name="FailoverSwitchModel",
        func=switch_model,
        description="Switch to an alternate model name on the same provider.",
    ),
    Tool(
        name="FailoverSwitchToken",
        func=switch_token,
        description="Rotate API token/credentials for the task.",
    ),
    Tool(
        name="FailoverSwitchUrl",
        func=switch_url,
        description="Point the task to an alternate endpoint URL for the same provider.",
    ),
    Tool(
        name="RetryAfterDelay",
        func=retry_after_delay,
        description="Retry operation with a delay (default 5 seconds).",
    ),
]
