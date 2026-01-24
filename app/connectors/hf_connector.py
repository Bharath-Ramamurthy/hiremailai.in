from typing import Optional, Dict
from huggingface_hub import InferenceClient
from .base_connector import BaseConnector
from core.logger import get_logger
from core.exceptions import HuggingFaceConnectorError

logger = get_logger(__name__)


class HuggingFaceConnector(BaseConnector):
    """
    Hugging Face connector for interacting with the Hugging Face Inference API.

    Good practice: Configuration (token, model, provider, api_url)
    should be passed explicitly from the factory or a configuration manager.
    This ensures better testability, separation of concerns, and flexibility
    when switching between environments or models.
    """

    def __init__(
        self,
        model: str,
        token: str,
        provider: str,
        api_url: Optional[str] = None
    ):
        self.model = model
        self.token = token
        self.provider = provider
        self.api_url = api_url
        self._client: Optional[InferenceClient] = None

    def _get_client(self) -> InferenceClient:
        """
        Lazily initialize and cache the InferenceClient instance.
        If already created, reuse the existing client.
        """
        if self._client:
            return self._client

        try:
            if self.api_url:
                self._client = InferenceClient(
                    api_key=self.token,
                    base_url=self.api_url
                )
            else:
                self._client = InferenceClient(api_key=self.token)

            return self._client

        except Exception as exc:
            logger.critical(f"Failed to initialize Hugging Face client: {exc}", exc_info=True)
            raise HuggingFaceConnectorError("Client initialization failed.") from exc

    def send_query(self, prompt: str, model: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Sends a prompt to the Hugging Face Inference API and returns a structured response.

        Args:
            prompt (str): User prompt or input text.
            model (Optional[str]): Optional model override.

        Returns:
            dict: {
                "status": "success" or "fail",
                "response": str or None,
                "error": str or None
            }
        """
        model_to_use = model or self.model
        client = self._get_client()

        try:
            completion = client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}]
            )

            if completion and getattr(completion, "choices", None):
                response_text = completion.choices[0].message.content.strip()
                return {"status": "success", "response": response_text, "error": None}

            logger.error("Empty or invalid completion response from Hugging Face API.")
            return {"status": "fail", "response": None, "error": "Empty or invalid completion response from Hugging Face API."}

        except Exception as exc:
            logger.exception("Hugging Face API request failed.")
            raise HuggingFaceConnectorError(f"Failed to get response from Hugging Face API: {exc}")
