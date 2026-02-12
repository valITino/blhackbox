"""Unified LLM client with provider fallback (OpenAI -> Anthropic -> Ollama)."""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from blhackbox.config import Settings
from blhackbox.config import settings as default_settings
from blhackbox.exceptions import LLMProviderError

logger = logging.getLogger("blhackbox.llm.client")


def get_llm(settings: Settings | None = None) -> BaseChatModel:
    """Return the first available LLM client based on provider priority.

    Tries providers in the order specified by LLM_PROVIDER_PRIORITY.
    Raises LLMProviderError if no provider is available.
    """
    cfg = settings or default_settings
    errors: list[str] = []

    for provider in cfg.provider_priority_list:
        try:
            llm = _build_provider(provider, cfg)
            if llm is not None:
                logger.info("Using LLM provider: %s", provider)
                return llm
        except Exception as exc:
            msg = f"{provider}: {exc}"
            logger.debug("Provider %s unavailable: %s", provider, exc)
            errors.append(msg)

    raise LLMProviderError(
        "No LLM provider available. Tried: "
        + ", ".join(cfg.provider_priority_list)
        + ". Errors: "
        + "; ".join(errors)
    )


def _build_provider(name: str, cfg: Settings) -> BaseChatModel | None:
    """Instantiate a LangChain chat model for the given provider name."""
    name = name.lower().strip()

    if name == "openai":
        if not cfg.openai_api_key:
            return None
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=cfg.openai_model,
            api_key=cfg.openai_api_key,
            temperature=0,
            max_tokens=4096,
        )

    if name == "anthropic":
        if not cfg.anthropic_api_key:
            return None
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=cfg.anthropic_model,
            api_key=cfg.anthropic_api_key,
            temperature=0,
            max_tokens=4096,
        )

    if name == "ollama":
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=cfg.ollama_model,
            base_url=cfg.ollama_url,
            temperature=0,
        )

    logger.warning("Unknown LLM provider: %s", name)
    return None
