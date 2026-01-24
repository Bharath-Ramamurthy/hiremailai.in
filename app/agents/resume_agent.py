# agents/resume_agent.py
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
from pylatexenc.latexencode import utf8tolatex

logger = get_logger(__name__)

class ResumeAgent(BaseAgent):
    TASK_NAME = "resume"
    PROMPT_KEY = "resume_generator"

    def __init__(
        self,
        resume_file: str,
        job_description: str,
        job_role: str,
        diagnostic_run: Optional[bool] = True,
        diagnostic_config: Optional[dict] = None
    ):
        super().__init__(diagnostic_run, diagnostic_config)
        self.resume_file = resume_file
        self.job_description = job_description
        self.job_role = job_role
        self.connector = get_connector(self.TASK_NAME)


    @staticmethod
    def escape_curly_braces(text: str) -> str:
        return text.replace("{", "{{").replace("}", "}}")
        
    @staticmethod
    def escape_latex_content(content: str) -> str:
      """Escapes only the content to be safely inserted in LaTeX."""
      return utf8tolatex(content)
    

        



    def run(self) -> Dict[str, Any]:
        try:
            # 1️⃣ Parse resume
            if not os.path.exists(self.resume_file):
                raise FileNotFoundError(f"Resume file not found: {self.resume_file}")
            parsed_resume = file_parser.read_tex_file(self.resume_file)
            if not parsed_resume.strip():
                raise ValueError("Parsed resume content is empty.")



            if self.PROMPT_KEY not in PROMPTS:
                raise ValueError(f"Prompt '{self.PROMPT_KEY}' not found.")
            prompt_template = PROMPTS[self.PROMPT_KEY] 


            #safe_resume = self.escape_latex_content(parsed_resume)
            safe_jd = self.escape_latex_content(self.job_description)
      
            #safe_jd = self.escape_curly_braces(self.job_description)
            #safe_resume = parsed_resume
            #safe_jd = self.job_description
            
            resume_prompt = prompt_template.format(resume_latex_code=parsed_resume, job_description=safe_jd, position=self.job_role)
            
            # 4️⃣ Connector

            resume_connector = self.connector
            logger.info("Sending resume generation prompt to connector...")

            # 5️⃣ Query LLM
            connector_response = resume_connector.send_query(resume_prompt)
            if not isinstance(connector_response, dict):
                raise TypeError(f"Unexpected connector response type: {type(connector_response)}")

            if connector_response.get("status") == "success":
                llm_response_raw = connector_response.get("response").strip()
                try:
                    safe_json_str = llm_response_raw.replace("\\", "\\\\")
                    llm_response = json.loads(llm_response_raw)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from LLM: {e}")
                    logger.debug(f"Raw LLM response: {llm_response_raw}")
                    raise
                   

                latex_code = llm_response["latex_code"]
                if not latex_code:
                    raise ValueError("LLM response missing 'latex_code'.")

                # Generate PDF
                resume_dir = os.getenv("RESUME_DIR", ".")
                os.makedirs(resume_dir, exist_ok=True)
                refined_resume_path = pdf_generator.generate_pdf(latex_code, "resume", resume_dir)
                logger.info(f"Refined resume generated: {refined_resume_path}")
                return {"status": "success", "path": refined_resume_path, "error_message": None}

            # Fail
            error_msg = connector_response.get("error", "Unknown LLM error.")
            logger.error(f"Connector failed: {error_msg}")
            raise RuntimeError(error_msg)

        except Exception as e:
            logger.error(f"Error occurred: {e}", exc_info=True)
            agent_args={
                    "resume_file": self.resume_file,
                    "job_description": self.job_description,
                    "job_role": self.job_role,
                    "diagnostic_run": True,
                    "diagnostic_config": {
                    "type": "connector_reconfig",
                    "diagnostic_connector": self.TASK_NAME}}
            retry_agent_factory = partial(ResumeAgent, **agent_args)
            return error_handler.handle_error(
                error=e,
                task=self.TASK_NAME,
                retry_callback=retry_agent_factory)

