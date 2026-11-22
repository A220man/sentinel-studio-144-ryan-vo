from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import openai


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider returns an error response."""


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters."""

    def __init__(self, api_key: str, endpoint: str, model: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model

    @abstractmethod
    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat completion request and return the content string."""
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the canonical provider name (e.g. 'openai', 'anthropic')."""
        ...


class OpenAIAdapter(LLMAdapter):
    """OpenAI-compatible adapter (including self-hosted OpenAI-compatible endpoints)."""

    def __init__(self, api_key: str, endpoint: str, model: str):
        super().__init__(api_key, endpoint, model)
        self.client = openai.OpenAI(base_url=endpoint.rstrip("/") + "/v1", api_key=api_key)

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except openai.APIError as e:
            raise LLMProviderError(f"OpenAI provider error: {e}") from e
        except Exception as e:
            raise LLMProviderError(f"Unexpected error from OpenAI adapter: {e}") from e

    def get_provider_name(self) -> str:
        return "openai"


class AnthropicAdapter(LLMAdapter):
    """Anthropic adapter placeholder — skeleton for future implementation."""

    def __init__(self, api_key: str, endpoint: str, model: str):
        super().__init__(api_key, endpoint, model)

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        raise NotImplementedError("Anthropic adapter not yet implemented")

    def get_provider_name(self) -> str:
        return "anthropic"


class GeminiAdapter(LLMAdapter):
    """Gemini adapter placeholder — skeleton for future implementation."""

    def __init__(self, api_key: str, endpoint: str, model: str):
        super().__init__(api_key, endpoint, model)

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        raise NotImplementedError("Gemini adapter not yet implemented")

    def get_provider_name(self) -> str:
        return "gemini"


class OllamaAdapter(LLMAdapter):
    """Ollama adapter placeholder — skeleton for future implementation."""

    def __init__(self, api_key: str, endpoint: str, model: str):
        super().__init__(api_key, endpoint, model)

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        raise NotImplementedError("Ollama adapter not yet implemented")

    def get_provider_name(self) -> str:
        return "ollama"


def get_adapter(
    provider: str,
    api_key: str,
    endpoint: str,
    model: str,
) -> LLMAdapter:
    """Factory to get the appropriate adapter for the given provider."""
    providers = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "gemini": GeminiAdapter,
        "ollama": OllamaAdapter,
    }
    adapter_class = providers.get(provider.lower())
    if adapter_class is None:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return adapter_class(api_key=api_key, endpoint=endpoint, model=model)
