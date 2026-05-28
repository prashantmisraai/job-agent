"""Provider-agnostic LLM factory for CrewAI agents."""

from __future__ import annotations

import os
from importlib.util import find_spec
from typing import Optional

from .config import GOOGLE_API_KEY, GROQ_API_KEY, LLM_MODEL, LLM_PROVIDER, OPENAI_API_KEY


UNSUPPORTED_MESSAGE_KEYS = {"cache_breakpoint"}


def _provider_model(provider: str, model: str) -> str:
    if "/" in model:
        return model

    if provider == "groq":
        return f"groq/{model}"
    if provider in {"openai", "azure", "anthropic", "gemini"}:
        return f"{provider}/{model}"
    return model


def _requires_litellm(provider: str) -> bool:
    return provider in {"groq", "openrouter", "deepseek"}


def _configure_litellm(provider: str) -> None:
    """Apply LiteLLM compatibility flags for non-native CrewAI providers."""

    if not _requires_litellm(provider):
        return

    os.environ.setdefault("LITELLM_DROP_PARAMS", "true")

    try:
        import litellm

        litellm.drop_params = True
    except ImportError:
        return


def _strip_unsupported_message_keys(value):
    if isinstance(value, list):
        return [_strip_unsupported_message_keys(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _strip_unsupported_message_keys(item)
            for key, item in value.items()
            if key not in UNSUPPORTED_MESSAGE_KEYS
        }
    return value


def get_crewai_llm(
    *,
    temperature: float = 0.2,
    model: Optional[str] = None,
    provider: Optional[str] = None,
):
    """Return a CrewAI-compatible LLM.

    The app defaults to Groq, but this function centralizes provider selection.
    Change ``LLM_PROVIDER`` and ``LLM_MODEL`` in the environment to move between
    Groq, OpenAI-compatible models, or Gemini without touching the agent code.
    """

    selected_provider = (provider or LLM_PROVIDER or "groq").lower()
    selected_model = model or LLM_MODEL

    if selected_provider == "groq" and GROQ_API_KEY:
        os.environ.setdefault("GROQ_API_KEY", GROQ_API_KEY)
    if selected_provider == "openai" and OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", OPENAI_API_KEY)
    if selected_provider in {"gemini", "google"} and GOOGLE_API_KEY:
        os.environ.setdefault("GOOGLE_API_KEY", GOOGLE_API_KEY)

    if _requires_litellm(selected_provider) and find_spec("litellm") is None:
        raise ImportError(
            f"Provider '{selected_provider}' requires LiteLLM for CrewAI. "
            "Install it with `pip install litellm` or switch LLM_PROVIDER to a "
            "native CrewAI provider such as `openai` or `gemini`."
        )

    _configure_litellm(selected_provider)

    from crewai import LLM

    model_name = _provider_model(selected_provider, selected_model)

    class CompatibleLLM(LLM):
        def _format_messages_for_provider(self, messages):
            formatted_messages = super()._format_messages_for_provider(messages)
            if _requires_litellm(selected_provider):
                return _strip_unsupported_message_keys(formatted_messages)
            return formatted_messages

        def _prepare_completion_params(self, messages, tools=None, skip_file_processing=False):
            params = super()._prepare_completion_params(messages, tools, skip_file_processing)
            if _requires_litellm(selected_provider) and "messages" in params:
                params["messages"] = _strip_unsupported_message_keys(params["messages"])
            return params

    try:
        return CompatibleLLM(model=model_name, temperature=temperature, drop_params=True)
    except TypeError:
        return CompatibleLLM(model=model_name, temperature=temperature)
