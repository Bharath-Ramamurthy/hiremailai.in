# connectors/factory.py
import os
from typing import Dict, Optional, Type
from app.connectors.base_connector import BaseConnector
from app.connectors import hf_connector, openai_connector, http_connector
from core.logger import get_logger

logger = get_logger(__name__)

# Cache single connector instance per task
_connector_instances: Dict[str, BaseConnector] = {}


class ConnectorFactory:
    """
    Factory Pattern for creating connector instances.
    Dynamically resolves connector classes based on type or environment config.
    """

    _registry: Dict[str, Type[BaseConnector]] = {}

    # Alias → canonical connector name map
    _canonical_map: Dict[str, str] = {
        "hf": "huggingface",
        "hugging_face": "huggingface",
        "oa": "openai",
        "rest": "http",
    }

    @classmethod
    def register_connector(cls, name: str, connector_cls: Type[BaseConnector]):
        """Register a connector implementation."""
        cls._registry[name.lower()] = connector_cls
        logger.debug(f"Registered connector type: {name}")

    @staticmethod
    def _get_env_var(base_name: str, alt_config: bool, allowlist: list[str], default: Optional[str]):
        """Helper for resolving environment variables with optional _ALT suffix."""
        base_upper = base_name.upper()
        if alt_config and any(param.upper() in base_upper for param in allowlist):
            env_key = f"{base_name}_ALT"
        else:
            env_key = base_name

        value = os.getenv(env_key, default)
        logger.debug(f"Resolved env {env_key} → {value}")
        return value

    @classmethod
    def create_connector(
        cls,
        connector_type: str,
        alt_config: bool = False,
        alt_param_allowlist: Optional[list[str]] = None,
        default: Optional[str] = None
    ) -> BaseConnector:
        """Create a connector instance using the registered factory."""
        alt_param_allowlist = alt_param_allowlist or []
        connector_type = connector_type.strip().lower()

        # Normalize alias to canonical connector type
        canon_type = cls._canonical_map.get(connector_type, connector_type)

        if canon_type not in cls._registry:
            raise ValueError(f"Unsupported connector type '{connector_type}'.")

        # --- Hugging Face Connector ---
        if canon_type == "huggingface":
            token = cls._get_env_var("HUGGINGFACE_CON_TOKEN", alt_config, alt_param_allowlist, default)
            model = cls._get_env_var("HUGGINGFACE_CON_MODEL", alt_config, alt_param_allowlist, default)
            provider = cls._get_env_var("HUGGINGFACE_CON_PROVIDER", alt_config, alt_param_allowlist, default)
            api_url = cls._get_env_var("HUGGINGFACE_CON_URL", alt_config, alt_param_allowlist, default)

            if not token or not model:
                raise ValueError("HUGGINGFACE_CON_TOKEN and HUGGINGFACE_CON_MODEL must be set in env.")

            return cls._registry[canon_type](
                token=token, model=model, provider=provider, api_url=api_url
            )

        # --- OpenAI Connector ---
        elif canon_type == "openai":
            api_key = cls._get_env_var("OPENAI_CON_API_TOKEN", alt_config, alt_param_allowlist, default)
            model = cls._get_env_var("OPENAI_CON_MODEL", alt_config, alt_param_allowlist, default)
            base_url = cls._get_env_var("OPENAI_CON_URL", alt_config, alt_param_allowlist, default)

            if not api_key or not model:
                raise ValueError("OPENAI_CON_API_TOKEN and OPENAI_CON_MODEL must be set in env.")

            return cls._registry[canon_type](base_url=base_url, api_key=api_key, model_name=model)

        # --- HTTP Connector ---
        elif canon_type == "http":
            api_url = cls._get_env_var("HTTP_CON_URL", alt_config, alt_param_allowlist, default)
            api_token = cls._get_env_var("HTTP_CON_API_TOKEN", alt_config, alt_param_allowlist, default)
            model = cls._get_env_var("HTTP_CON_MODEL", alt_config, alt_param_allowlist, default)

            if not api_url or not api_token:
                raise ValueError("HTTP_CON_URL and HTTP_CON_API_TOKEN must be set in env.")

            return cls._registry[canon_type](api_url=api_url, api_token=api_token, model_name=model)

        raise ValueError(f"No factory handler for connector type '{connector_type}'.")


def get_connector(
    task: str,
    reload: bool = False,
    override_type: Optional[str] = None,
    alt_config: bool = False,
    alt_param_allowlist: Optional[list[str]] = None,
    default: Optional[str] = None
) -> BaseConnector:
    """
    Factory access function.
    Returns cached connector instance per task (unless reload=True).
    """
    key = task.lower()
    alt_param_allowlist = alt_param_allowlist or []

    if not reload and key in _connector_instances:
        return _connector_instances[key]

    connector_type = (
        override_type
        or os.getenv(f"{task.upper()}_AGENT_CONNECTOR")
        or os.getenv("DEFAULT_CONNECTOR")
    )

    if not connector_type:
        raise ValueError(f"No connector type configured for task '{task}'.")

    # Create connector via the factory
    connector = ConnectorFactory.create_connector(
        connector_type=connector_type,
        alt_config=alt_config,
        alt_param_allowlist=alt_param_allowlist,
        default=default
    )

    _connector_instances[key] = connector
    return connector


# -----------------------------------------
# Register built-in connectors
# -----------------------------------------
ConnectorFactory.register_connector("huggingface", hf_connector.HuggingFaceConnector)
ConnectorFactory.register_connector("openai", openai_connector.OpenAIConnector)
ConnectorFactory.register_connector("http", http_connector.HTTPConnector)
