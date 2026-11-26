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
    """Anthropic adapter for Claude models."""

    def __init__(self, api_key: str, endpoint: str, model: str):
        super().__init__(api_key, endpoint, model)
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key, base_url=endpoint.rstrip("/") if endpoint else None)

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            # Anthropic uses a different message format - convert from OpenAI format
            content = ""
            for msg in messages:
                role = msg.get("role", "user")
                text = msg.get("content", "")
                if role == "system":
                    content += f"\n\nSystem: {text}"
                elif role == "user":
                    content += f"\n\nUser: {text}"
                elif role == "assistant":
                    content += f"\n\nAssistant: {text}"

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 1000,
                temperature=temperature,
                messages=[{"role": "user", "content": content.strip()}],
            )
            # Extract text from Anthropic response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return ""
        except Exception as e:
            raise LLMProviderError(f"Anthropic provider error: {e}") from e

    def get_provider_name(self) -> str:
        return "anthropic"


class GeminiAdapter(LLMAdapter):
    """Gemini adapter for Google models."""

    def __init__(self, api_key: str, endpoint: str, model: str):
        super().__init__(api_key, endpoint, model)
        import google.generativeai as genai
        self.endpoint = endpoint.rstrip("/") if endpoint else None
        genai.configure(api_key=api_key)
        if self.endpoint:
            # For custom endpoints, configure appropriately
            genai.configure(endpoint=self.endpoint)
        self.model = genai.GenerativeModel(self.model)

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            # Convert messages to Gemini format - take the last user message
            user_text = ""
            for msg in reversed(messages):
                role = msg.get("role", "user")
                text = msg.get("content", "")
                if role == "user":
                    user_text = text
                    break
            if not user_text:
                user_text = messages[-1].get("content", "")

            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens or 1000,
            }
            response = self.model.generate_content(
                user_text,
                generation_config=generation_config,
            )
            return response.text or ""
        except Exception as e:
            raise LLMProviderError(f"Gemini provider error: {e}") from e

    def get_provider_name(self) -> str:
        return "gemini"


class OllamaAdapter(LLMAdapter):
    """Ollama adapter for local LLMs."""

    def __init__(self, api_key: str, endpoint: str, model: str):
        super().__init__(api_key, endpoint, model)
        import ollama
        self.endpoint = endpoint.rstrip("/") if endpoint else "http://localhost:11434"
        self.client = ollama

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            # Ollama uses a different format
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                },
            )
            if response and "message" in response and "content" in response["message"]:
                return response["message"]["content"]
            return ""
        except Exception as e:
            raise LLMProviderError(f"Ollama provider error: {e}") from e

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
