# connectors/base_connector.py
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseConnector(ABC):
    """
    Abstract base class for all LLM connector implementations.
    Defines the common interface expected by the factory and higher-level agents.
    """

    @abstractmethod
    def send_query(self, prompt: str, **kwargs: Any) -> str:
        """
        Send a text prompt or query to the underlying model/service.
        Implementations must return the model's textual response.
        """
        pass

    def __repr__(self) -> str:
        """Readable identifier for debugging/logging."""
        return f"<{self.__class__.__name__}>"
