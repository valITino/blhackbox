"""Unified LLM client — DEPRECATED in blhackbox v2.0.

The new architecture separates concerns:
  - Claude operates externally as the MCP Host orchestrator
  - Ollama runs locally as the preprocessing backend, accessed via
    the blhackbox aggregator MCP server's agent classes

The LLM provider fallback chain (OpenAI -> Anthropic -> Ollama) is no
longer used.  Claude and Ollama serve distinct, non-interchangeable
roles.  There is no fallback.

This module is preserved for backwards compatibility with code that
still imports ``get_llm``.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from blhackbox.config import Settings
from blhackbox.config import settings as default_settings
from blhackbox.exceptions import LLMProviderError

logger = logging.getLogger("blhackbox.llm.client")


def _is_openai_reasoning_model(model: str) -> bool:
    """Check if an OpenAI model is an o-series reasoning model (o1, o3, etc.).

    Reasoning models do not support the temperature parameter.
    """
    return model.startswith("o") and len(model) > 1 and model[1:2].isdigit()


def get_llm(settings: Settings | None = None) -> BaseChatModel:
    """Return the first available LLM client based on provider priority.

    .. deprecated:: 2.0
        The LLM provider fallback chain is deprecated.  Claude operates
        externally as the MCP Host.  Ollama is accessed directly via the
        aggregator MCP server's agent classes using httpx.

    Tries providers in the order specified by LLM_PROVIDER_PRIORITY.
    Raises LLMProviderError if no provider is available.
    """
    warnings.warn(
        "get_llm() is deprecated in blhackbox v2.0. "
        "Claude operates externally as the MCP Host; "
        "Ollama is accessed via the aggregator MCP server's agent classes.",
        DeprecationWarning,
        stacklevel=2,
    )
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

        kwargs: dict[str, Any] = {
            "model": cfg.openai_model,
            "api_key": cfg.openai_api_key,
            "max_tokens": 4096,
        }
        # o-series reasoning models (o1, o3, etc.) do not support temperature
        if not _is_openai_reasoning_model(cfg.openai_model):
            kwargs["temperature"] = 0

        return ChatOpenAI(**kwargs)

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
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=cfg.ollama_model,
            base_url=cfg.ollama_url,
            temperature=0,
        )

    logger.warning("Unknown LLM provider: %s", name)
    return None
