# agents/cover_letter_agent.py
import os
import json
import re
from typing import Optional, Dict, Any
from app.file_utils import file_parser, pdf_generator
from core.logger import get_logger
from core.exceptions import DiagnosticToolError
from .base_agent import BaseAgent
from core.prompt_loader import PROMPTS
from core import error_handler
from app.connectors import get_connector
from functools import partial

logger = get_logger(__name__)


class CoverLetterAgent(BaseAgent):
    TASK_NAME = "cover_letter"
    PROMPT_KEY = "cover_letter_generator"

    def __init__(
        self,
        refined_resume_path: str,
        job_role: str,
        job_description: str,
        company: str,
        diagnostic_run: Optional[bool] = True,
        diagnostic_config: Optional[dict] = None,
    ):
        super().__init__(diagnostic_run, diagnostic_config)
        self.refined_resume_path = refined_resume_path
        self.job_role = job_role
        self.job_description = job_description
        self.company = company
        self.connector = get_connector(self.TASK_NAME)

    def run(self) -> Dict[str, Any]:
        try:
            # 1️⃣ Parse resume
            if not os.path.exists(self.refined_resume_path):
                raise FileNotFoundError(f"Resume file not found: {self.refined_resume_path}")

            parsed_resume = file_parser.extract_text_from_pdf(self.refined_resume_path)
            if not parsed_resume.strip():
                raise ValueError("Parsed resume content is empty.")

            # 2️⃣ Load prompt
            if self.PROMPT_KEY not in PROMPTS:
                raise ValueError(f"Prompt '{self.PROMPT_KEY}' not found.")
            prompt_template = PROMPTS[self.PROMPT_KEY]
            cover_letter_prompt = prompt_template.format(resume_text=parsed_resume, job_description = self.job_description, company=self.company, position=self.job_role)

            # 4️⃣ Get connector
            connector = self.connector
            logger.info("Sending cover letter generation prompt to connector...")

            # 5️⃣ Query LLM
            connector_response = connector.send_query(cover_letter_prompt)
            if not isinstance(connector_response, dict):
                raise TypeError(f"Unexpected connector response type: {type(connector_response)}")

            if connector_response.get("status") == "success":
                llm_response_raw = connector_response.get("response").strip()

                try:
                    llm_response = json.loads(llm_response_raw)
         
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from LLM: {e}")
                    logger.debug(f"Raw LLM response: {llm_response_raw}")
                    raise
                
                latex_code = llm_response.get("latex_code")
                if not latex_code:
                    raise ValueError("LLM response missing 'latex_code'.")

                # 6️⃣ Generate PDF
                output_dir = os.getenv("COVER_LETTER_DIR", ".")
                os.makedirs(output_dir, exist_ok=True)
                pdf_path = pdf_generator.generate_pdf(latex_code, "cover_letter", output_dir)

                logger.info(f"Cover letter generated successfully: {pdf_path}")
                return {"status": "success", "path": pdf_path, "error_message": None}

            # LLM responded with failure
            error_msg = connector_response.get("error", "Unknown LLM error.")
            logger.error(f"Connector failed: {error_msg}")
            raise RuntimeError(error_msg)

        except Exception as e:
            logger.error(f"Error occurred in {self.TASK_NAME}: {e}", exc_info=True)
            agent_args={
                    "refined_resume_path": self.refined_resume_path,
                    "job_role": self.job_role,
                    "company": self.company,
                    "diagnostic_run": True,
                    "diagnostic_config": {
                        "type": "connector_reconfig",
                        "diagnostic_connector": self.TASK_NAME
                    }}
            retry_agent_factory = partial(CoverLetterAgent, **agent_args)
            return error_handler.handle_error( error=e,task=self.TASK_NAME, retry_callback=retry_agent_factory)

