from __future__ import annotations

from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional


class LLMProviderRequest(BaseModel):
    """Request model for LLM provider configuration."""

    provider: str = Field(..., description="LLM provider name: openai, anthropic, gemini, ollama")
    model: str = Field(..., description="Model identifier string")
    endpoint: Optional[str] = Field(
        None, description="Custom endpoint URL for OpenAI-compatible or self-hosted providers"
    )
    api_key: str = Field(..., description="API key for the provider")

    @validator("provider")
    def provider_must_be_valid(cls, v: str) -> str:
        valid = {"openai", "anthropic", "gemini", "ollama"}
        if v.lower() not in valid:
            raise ValueError(f"Provider must be one of {valid}")
        return v.lower()


class LLMChatMessage(BaseModel):
    """Individual message in a chat completion request."""

    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content text")

    @validator("role")
    def role_must_be_valid(cls, v: str) -> str:
        if v not in {"system", "user", "assistant"}:
            raise ValueError("Role must be one of: system, user, assistant")
        return v


class LLMChatCompletionRequest(BaseModel):
    """Request model for chat completion."""

    messages: List[LLMChatMessage] = Field(
        ..., description="List of chat messages"
    )
    temperature: float = Field(
        0.0, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, description="Maximum tokens in response"
    )

    @validator("messages")
    def messages_must_not_be_empty(cls, v: List[LLMChatMessage]) -> List[LLMChatMessage]:
        if not v:
            raise ValueError("Messages list must not be empty")
        return v


class LLMChatCompletionResponse(BaseModel):
    """Response model for chat completion."""

    content: str = Field(..., description="Generated response text")
    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model identifier")
    usage: Optional[Dict[str, int]] = Field(
        None, description="Token usage if available"
    )
    advisory: bool = Field(
        True, description="Whether the explanation is labeled as advisory"
    )
    grounded: bool = Field(
        True, description="Whether the explanation is grounded in findings"
    )


class ProviderConfigResponse(BaseModel):
    """Response model for provider configuration."""

    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model identifier")
    endpoint: Optional[str] = Field(None, description="Configured endpoint URL")
    available: bool = Field(True, description="Provider is available/configured")
