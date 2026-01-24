# core/error_handler.py
import inspect
from typing import Optional, Callable
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent
from app.connectors.diagnostic_tools import LANGCHAIN_TOOLS
from core.logger import get_logger
from .prompt_loader import PROMPTS
import os
logger = get_logger(__name__)

# -----------------------------
# Initialize Diagnostic Agent
# -----------------------------

try:
    llm = ChatOpenAI(temperature=0,
    openai_api_base=os.getenv("DIAGNOSTIC_TOOL_CON_URL"),
    model =os.getenv("DIAGNOSTIC_TOOL_CON_MODEL"),
    openai_api_key=os.getenv("DIAGNOSTIC_TOOL_CON_API_TOKEN"))
    diagnostic_agent = initialize_agent(
        tools=LANGCHAIN_TOOLS,    
        llm=llm,
        agent="zero-shot-react-description",
        verbose=True
    )
except Exception as init_error:
    logger.critical(f"Failed to initialize diagnostic agent: {init_error}", exc_info=True)
    diagnostic_agent = None


# -----------------------------
# Tool Function Mapping
# -----------------------------
TOOL_FUNC_MAP = {
    "switch connector": "FailoverSwitchConnector",
    "switch config": "FailoverSwitchConfig",
    "switch model": "FailoverSwitchModel",
    "switch token": "FailoverSwitchToken",
    "switch url": "FailoverSwitchUrl",
    "retry after delay": "RetryAfterDelay",
}


# -----------------------------
# Core Error Handler
# -----------------------------
def handle_error(
    error: Exception,
    task: str,
    retry_callback: Optional[Callable[..., dict]] = None,
) -> dict:
    """
    Centralized error handler that uses a LangChain diagnostic agent to diagnose and fix connector issues.

    Parameters:
        error: Exception that triggered the handler.
        task: The connector or process name (e.g., 'resume', 'cover_letter').
        retry_callback: Function to retry the failed operation.
        agent_arguments: Arguments for retry_callback.
    """

    PROMPT_KEY  = "error_handler"


    if not diagnostic_agent:
        logger.error("Diagnostic agent not initialized — skipping automatic recovery.")
        return {"status": "fail", "error_message": str(error)}

    try:
        # 1️⃣ Create diagnostic prompt
        if PROMPT_KEY not in PROMPTS:
                raise ValueError(f"Prompt '{PROMPT_KEY}' not found.")
        prompt_template = PROMPTS[PROMPT_KEY]
        prompt = prompt_template.format(connector_type=task.lower(), error = str(error))
        
        logger.info(f"Running diagnostic agent with prompt: {prompt}")

        # 2️⃣ Get agent response
        response = diagnostic_agent.run(prompt)
        logger.info(f"Raw diagnostic response: {response}")

        # Normalize response
        action = response.strip().lower()

        # 3️⃣ Match to a registered tool
        selected_tool_name = TOOL_FUNC_MAP.get(action)
        if not selected_tool_name:
            logger.warning(f"No matching tool found for response: '{action}'")
            return {"status": "fail", "error_message": f"No diagnostic action found for '{action}'"}

        # 4️⃣ Find the actual LangChain Tool object
        tool = next((t for t in LANGCHAIN_TOOLS if t.name == selected_tool_name), None)
        if not tool:
            logger.error(f"Tool '{selected_tool_name}' not found in LANGCHAIN_TOOLS.")
            return {"status": "fail", "error_message": f"Tool '{selected_tool_name}' not registered."}

        # 5️⃣ Execute the tool function
        logger.info(f"Executing recovery tool '{selected_tool_name}' for task '{task}'...")
        sig = inspect.signature(tool.func)
        accepted_args = {k: v for k, v in {"task": task}.items() if k in sig.parameters}
        tool.func(**accepted_args)

        # 6️⃣ Retry the operation if callback provided
        if retry_callback:
            logger.info(f"Retrying task '{task}' after recovery action...")
            agent_instance = retry_callback()
            result = agent_instance.run()
            return result

        logger.info(f"Recovery tool '{selected_tool_name}' executed successfully (no retry callback provided).")
        return {"status": "success", "message": f"Tool '{selected_tool_name}' executed."}

    except Exception as e:
        logger.critical(f"Diagnostic handler failed during execution: {e}", exc_info=True)
        return {"status": "fail", "error_message": str(e)}
