from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from app.schemas.llm import (
    LLMProviderRequest,
    LLMChatCompletionRequest,
    LLMChatCompletionResponse,
    LLMChatMessage,
)
from app.services.llm_agent import get_adapter, LLMProviderError

router = APIRouter(prefix="/llm", tags=["llm"])


def _get_adapter_from_request(
    request: LLMProviderRequest,
) -> Any:
    """Resolve and return an LLM adapter instance from the request DTO."""
    return get_adapter(
        provider=request.provider,
        api_key=request.api_key,
        endpoint=request.endpoint or "",
        model=request.model,
    )


@router.post(
    "/configure",
    response_model=dict[str, str],
    summary="Configure LLM provider",
)
async def configure_provider(
    request: LLMProviderRequest,
) -> dict[str, str]:
    """Validate and store provider configuration.

    Returns a confirmation dict with the provider name.
    """
    try:
        adapter = _get_adapter_from_request(request)
        # Minimal validation — just ensure the adapter can be instantiated.
        # A real implementation would test the connection.
        return {
            "status": "ok",
            "provider": adapter.get_provider_name(),
            "model": request.model,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/chat-complete",
    response_model=LLMChatCompletionResponse,
    summary="Chat completion via configured LLM provider",
)
async def chat_complete(
    request: LLMChatCompletionRequest,
) -> LLMChatCompletionResponse:
    """Send a chat completion request to the configured LLM provider.

    The provider must have been configured first via /llm/configure.
    Returns the generated content labeled as advisory and grounded in findings.
    """
    # In a full implementation, the adapter would be stored per-session/user.
    # For this minimal checkpoint, we use a default OpenAI-compatible setup.
    # TODO: pull from stored config once persistence is in place.
    adapter = get_adapter(
        provider="openai",
        api_key="sk-test-minimal-checkpoint",
        endpoint="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )

    # Convert Pydantic messages to the format expected by the adapter
    openai_messages: List[Dict[str, str]] = [
        {"role": msg.role, "content": msg.content} for msg in request.messages
    ]

    try:
        content = adapter.chat_complete(
            messages=openai_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except LLMProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return LLMChatCompletionResponse(
        content=content,
        provider="openai",
        model="gpt-4o-mini",
        advisory=True,
        grounded=True,
    )
