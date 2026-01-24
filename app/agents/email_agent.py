# agents/email_agent.py
import os
import json
import re
from typing import Optional, Dict, Any
from app.file_utils import file_parser
from app.email_utils.gmail_sender import send_email_with_attachment
from core.logger import get_logger
from core.exceptions import DiagnosticToolError
from .base_agent import BaseAgent
from core.prompt_loader import PROMPTS
from core import error_handler 
from app.connectors import get_connector
from functools import partial

logger = get_logger(__name__)

class EmailAgent(BaseAgent):
    TASK_NAME = "email"
    PROMPT_KEY = "email_generator"

    def __init__(
        self,
        resume_path: str,
        position: str,
        job_description: str,
        company: str,
        receiver_email: str,
        attach_cover_letter: Optional[bool] = False,
        cover_letter_path: Optional[str] = None,
        diagnostic_run: Optional[bool] = True,
        diagnostic_config: Optional[dict] = None
    ):
        super().__init__(diagnostic_run, diagnostic_config)
        self.resume_path = resume_path
        self.position = position
        self.job_description = job_description
        self.company = company
        self.receiver_email = receiver_email
        self.attach_cover_letter = attach_cover_letter
        self.cover_letter_path = cover_letter_path
        self.connector = get_connector(self.TASK_NAME)

    def run(self) -> Dict[str, Any]:
        try:
            # 1️⃣ Parse resume
            if not os.path.exists(self.resume_path):
                raise FileNotFoundError(f"Resume file not found: {self.resume_path}")
            parsed_resume = file_parser.extract_text_from_pdf(self.resume_path)
            if not parsed_resume.strip():
                raise ValueError("Parsed resume content is empty.")

            # 2️⃣ Load prompt
            
            if self.PROMPT_KEY not in PROMPTS:
                raise ValueError(f"Prompt '{self.PROMPT_KEY}' not found.")
            prompt_template = PROMPTS[self.PROMPT_KEY]           
            email_prompt = prompt_template.format(
                position=self.position,
                resume_text=parsed_resume,
                job_description=self.job_description,
                company=self.company)
           
            # 4️⃣ Connector
            email_connector = self.connector
            logger.info("Sending email generation prompt to connector...")

            # 5️⃣ Query LLM
            connector_response = email_connector.send_query(email_prompt)
            if not isinstance(connector_response, dict):
                raise TypeError(f"Unexpected connector response type: {type(connector_response)}")

            if connector_response.get("status") == "success":
                llm_response_raw = connector_response.get("response").strip()
     
                try:
                    llm_response = json.loads(llm_response_raw)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from LLM: {e}")
                    logger.debug(f"Raw LLM response: {llm_response_raw}")
                    raise


                email_body_text = llm_response.get("html_code")
                email_subject = llm_response.get("email_subject")
                if not email_body_text or not email_subject:
                    raise ValueError("LLM response missing 'html_code' / 'email_subject'.")

                # 6️⃣ Send email
                if self.attach_cover_letter and self.cover_letter_path:
                    email_status = send_email_with_attachment(
                        self.receiver_email, email_subject, email_body_text, self.resume_path, self.cover_letter_path
                    )
                else:
                    email_status = send_email_with_attachment(self.receiver_email, email_subject, email_body_text, self.resume_path)

                logger.info(f"Email sent successfully: {email_status}")
                return {"status": "success", "path": self.resume_path, "error_message": None}

            # LLM responded with failure
            error_msg = connector_response.get("error", "Unknown LLM error.")
            logger.error(f"Connector failed: {error_msg}")
            raise RuntimeError(error_msg)

        except Exception as e:
            logger.error(f"Error occurred: {e}", exc_info=True)
            agent_args={
                    "resume_path": self.resume_path,
                    "position": self.position,
                    "job_description": self.job_description,
                    "company": self.company,
                    "receiver_email": self.receiver_email,
                    "attach_cover_letter": self.attach_cover_letter,
                    "cover_letter_path": self.cover_letter_path,
                    "diagnostic_run": True,
                    "diagnostic_config": {"type": "connector_reconfig", "diagnostic_connector": self.TASK_NAME}}
            retry_agent_factory = partial(EmailAgent, **agent_args)
            return error_handler.handle_error(
                error=e,
                task=self.TASK_NAME,
                retry_callback=retry_agent_factory)

