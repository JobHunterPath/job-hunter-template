"""
Provider-agnostic LLM client.

Supported providers: anthropic | openai | google | ollama

All providers expose the same complete() interface — callers don't know
or care which SDK is underneath. Configure per pipeline role in api_config.yml:

  llm:
    default_provider: anthropic
    providers:
      validation:   anthropic      # cheap/fast bulk calls
      tailoring:    openai         # override per role
    models:
      validation:   claude-haiku-4-5-20251001
      tailoring:    gpt-4o

Use get_llm_client(role) wherever a model call is needed.
"""

import logging
from typing import ClassVar

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Thin facade over provider SDKs (Strategy pattern).

    Each provider is a branch in complete() — add new providers by adding
    a branch in _init_client() and complete() without touching callers.
    """

    def __init__(self, provider: str, api_key: str = "", base_url: str = "") -> None:
        self._provider = provider
        self._raw = self._init_client(provider, api_key, base_url)

    # ── SDK construction ───────────────────────────────────────────────────────

    def _init_client(self, provider: str, api_key: str, base_url: str):
        if provider == "anthropic":
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError("pip install anthropic")
            return Anthropic(api_key=api_key)

        if provider == "openai":
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("pip install openai")
            return OpenAI(api_key=api_key)

        if provider == "google":
            try:
                import google.generativeai as genai
            except ImportError:
                raise ImportError("pip install google-generativeai")
            genai.configure(api_key=api_key)
            return genai

        if provider == "ollama":
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("pip install openai  # Ollama uses the OpenAI-compatible API")
            # Ollama exposes an OpenAI-compatible endpoint; api_key is ignored server-side
            return OpenAI(
                base_url=base_url or "http://localhost:11434/v1",
                api_key="ollama",
            )

        raise ValueError(
            f"Unknown LLM provider: {provider!r}. "
            "Supported: anthropic | openai | google | ollama"
        )

    # ── Unified interface ──────────────────────────────────────────────────────

    def complete(
        self,
        *,
        system: str = "",
        user: str,
        model: str,
        max_tokens: int,
    ) -> str:
        """
        Send a prompt and return the response as a plain string.

        Args:
            system:     System / instruction prompt. May be empty.
            user:       User message content.
            model:      Provider-specific model identifier.
            max_tokens: Maximum tokens to generate.

        Returns:
            Stripped response text.
        """
        logger.debug(
            f"[llm] provider={self._provider} model={model} max_tokens={max_tokens}"
        )

        if self._provider == "anthropic":
            kwargs: dict = dict(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": user}],
            )
            if system:
                kwargs["system"] = system
            resp = self._raw.messages.create(**kwargs)
            return resp.content[0].text.strip()

        if self._provider in ("openai", "ollama"):
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": user})
            resp = self._raw.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
            )
            return resp.choices[0].message.content.strip()

        if self._provider == "google":
            init_kwargs: dict = {"model_name": model}
            if system:
                init_kwargs["system_instruction"] = system
            model_obj = self._raw.GenerativeModel(**init_kwargs)
            resp = model_obj.generate_content(
                user,
                generation_config={"max_output_tokens": max_tokens},
            )
            return resp.text.strip()

        raise RuntimeError(f"[llm] Unhandled provider: {self._provider}")


# ── Factory with per-provider caching ─────────────────────────────────────────

_cache: dict[str, LLMClient] = {}


def get_llm_client(role: str) -> LLMClient:
    """
    Return a cached LLMClient for the given pipeline role.

    Provider and credentials are resolved from api_config.yml.
    Clients are cached per provider — two roles sharing the same provider
    reuse the same connection object.

    Args:
        role: Pipeline stage name (validation | scoring | tailoring |
              cover_letter | discovery). Must match keys in api_config.yml.
    """
    from core.config import load_api_config, get_secret

    cfg = load_api_config()
    llm = cfg.get("llm", {})

    provider: str = (
        llm.get("providers", {}).get(role)
        or llm.get("default_provider", "anthropic")
    )

    if provider in _cache:
        return _cache[provider]

    secrets = cfg.get("secrets", {})
    provider_cfg = secrets.get(provider, {})

    if provider == "ollama":
        api_key = ""
        base_url = cfg.get("ollama", {}).get("base_url", "http://localhost:11434")
    else:
        env_var = provider_cfg.get("env_var", "")
        required = provider_cfg.get("required", False)
        api_key = get_secret(env_var, required=required) if env_var else ""
        base_url = ""

    logger.info(f"[llm] Initialising {provider} client (role: {role})")
    client = LLMClient(provider, api_key=api_key, base_url=base_url)
    _cache[provider] = client
    return client
