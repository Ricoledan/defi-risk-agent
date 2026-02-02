"""LLM provider configuration with Ollama as default."""

import os
from dataclasses import dataclass
from enum import Enum

import httpx
from langchain_core.language_models import BaseChatModel


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    api_key: str | None = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables."""
        provider_str = os.getenv("LLM_PROVIDER", "ollama").lower()

        if provider_str == "openai":
            return cls(
                provider=LLMProvider.OPENAI,
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY"),
            )
        elif provider_str == "anthropic":
            return cls(
                provider=LLMProvider.ANTHROPIC,
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        else:
            return cls(
                provider=LLMProvider.OLLAMA,
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            )


def check_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama server is running."""
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
        return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False


def get_available_ollama_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Get list of available Ollama models."""
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
    except (httpx.RequestError, httpx.TimeoutException):
        pass
    return []


def get_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """
    Get LLM instance based on configuration.

    Defaults to Ollama with llama3.2 if no config provided.
    Falls back gracefully if Ollama is not available.
    """
    if config is None:
        config = LLMConfig.from_env()

    if config.provider == LLMProvider.OLLAMA:
        from langchain_ollama import ChatOllama

        if not check_ollama_available(config.base_url):
            raise RuntimeError(
                f"Ollama server not available at {config.base_url}. Start it with: ollama serve"
            )

        available_models = get_available_ollama_models(config.base_url)
        if available_models and config.model not in available_models:
            # Try to find a matching model
            base_model = config.model.split(":")[0]
            matches = [m for m in available_models if m.startswith(base_model)]
            if matches:
                config.model = matches[0]
            else:
                raise RuntimeError(
                    f"Model '{config.model}' not found. "
                    f"Available: {', '.join(available_models)}. "
                    f"Pull it with: ollama pull {config.model}"
                )

        return ChatOllama(
            model=config.model,
            base_url=config.base_url,
            temperature=config.temperature,
        )

    elif config.provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        if not config.api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable required")

        return ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
        )

    elif config.provider == LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        if not config.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable required")

        return ChatAnthropic(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
        )

    else:
        raise ValueError(f"Unknown provider: {config.provider}")


# Singleton for reuse
_llm_instance: BaseChatModel | None = None


def get_default_llm() -> BaseChatModel:
    """Get or create default LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_llm()
    return _llm_instance


def reset_llm() -> None:
    """Reset the LLM instance (useful for testing)."""
    global _llm_instance
    _llm_instance = None
