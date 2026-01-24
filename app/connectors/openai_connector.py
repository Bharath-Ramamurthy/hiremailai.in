from openai import OpenAI
from .base_connector import BaseConnector
from core.logger import get_logger
from core.exceptions import OpenAIConnectorError

logger = get_logger(__name__)


class OpenAIConnector(BaseConnector):
    """
    Connector for interacting with OpenAI or OpenRouter chat completion APIs.
    """

    def __init__(self, base_url: str, api_key: str, model_name: str):
        """
        Initializes the OpenAI connector with base URL, API key, and model name.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        try:
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        except Exception as exc:
            logger.critical(f"Failed to initialize OpenAI client: {exc}", exc_info=True)
            raise OpenAIConnectorError("Client initialization failed.") from exc

    def send_query(self, prompt: str, temperature: float = 0.7) -> dict:
        """
        Sends a chat completion request and returns structured response.

        Args:
            prompt (str): User input text.
            temperature (float): Sampling temperature for output diversity.

        Returns:
            dict: {
                "status": "success" or "fail",
                "response": str or None,
                "error": str or None
            }

        Raises:
            OpenAIConnectorError: On any API or client failure.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )

            if completion and completion.choices:
                content = completion.choices[0].message.content.strip()
                return {"status": "success", "response": content, "error": None}

            logger.error("Empty or invalid completion response from OpenAI API.")
            return {
                "status": "fail",
                "response": None,
                "error": "Empty or invalid completion response from OpenAI API."
            }

        except Exception as exc:
            logger.critical(f"OpenAIConnectorError: {exc}", exc_info=True)
            raise OpenAIConnectorError(f"Failed to get response from OpenAI API: {exc}") from exc
