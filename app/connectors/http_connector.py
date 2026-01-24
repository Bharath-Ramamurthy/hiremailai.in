import requests
from .base_connector import BaseConnector
from core.logger import get_logger
from core.exceptions import HTTPConnectorError

logger = get_logger(__name__)


class HTTPConnector(BaseConnector):
    """
    A connector for interacting with custom HTTP-based LLM APIs.
    It expects a JSON response that may follow OpenAI-style or custom schema.
    """

    def __init__(self, api_url: str, api_token: str, model_name: str):
        """
        Initializes the HTTP connector with URL, token, and model name.
        """
        self.api_url = api_url
        self.api_token = api_token
        self.model_name = model_name
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def send_query(self, prompt: str, temperature: float = 0.7):
        """
        Sends a prompt to the configured HTTP API endpoint.
        Returns the model's response in a structured format.

        Args:
            prompt (str): Input text to send to the API.
            temperature (float): Sampling temperature for generation.

        Returns:
            dict: {
                "status": "success" or "fail",
                "response": str or None,
                "error": str or None
            }

        Raises:
            HTTPConnectorError: On any network or response error.
        """
        payload = {
            "prompt": prompt,
            "model": self.model_name,
            "temperature": temperature
        }

        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Handle OpenAI-style response
            if isinstance(data, dict) and "choices" in data and data["choices"]:
                message = data["choices"][0].get("message", {})
                content = message.get("content", "")
                return {"status": "success", "response": content.strip(), "error": None}

            # Handle simpler response structure
            elif isinstance(data, dict) and "response" in data:
                return {"status": "success", "response": data["response"], "error": None}

            logger.error("Empty or invalid response structure received from API.")
            return {"status": "fail", "response": None, "error": "Empty or invalid response structure received from API."}

        except requests.exceptions.RequestException as e:
            logger.exception("HTTP request failed while connecting to LLM API.")
            raise HTTPConnectorError(f"HTTP request failed: {e}") from e

        except ValueError as e:
            logger.exception("Invalid JSON response received from API.")
            raise HTTPConnectorError(f"Invalid JSON response: {e}") from e
