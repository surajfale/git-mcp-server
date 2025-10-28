"""AI client for generating commit messages using OpenAI-compatible APIs.

This module currently supports OpenAI gpt-4o-mini via the official OpenAI SDK.
It also supports overriding base_url for OpenAI-compatible servers.
"""
from __future__ import annotations

import os
import time
from typing import Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled by config validation/docs
    OpenAI = None  # type: ignore

from .config import ServerConfig


class AIClient:
    """Thin wrapper around an LLM to generate Conventional Commit messages."""

    def __init__(self, config: ServerConfig) -> None:
        if not config.enable_ai:
            raise ValueError("AI is disabled in configuration")
        if config.ai_provider != "openai":
            raise ValueError("Only 'openai' provider is supported currently")
        if OpenAI is None:
            raise ImportError("openai package is not installed")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")

        # Instantiate client, optionally override base_url
        kwargs = {}
        if config.ai_base_url:
            kwargs["base_url"] = config.ai_base_url
        self._client = OpenAI(api_key=api_key, **kwargs)
        self._model = config.ai_model
        self._temperature = float(config.ai_temperature)
        self._max_tokens = int(config.ai_max_tokens)
        self._timeout = int(config.ai_timeout_seconds)

    def generate_commit_message(self, prompt: str) -> str:
        """Call the model and return the commit message text.

        The model is instructed to return the Conventional Commit message only.
        """
        start = time.time()
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior engineer who writes excellent Conventional Commit messages. "
                            "Output must be ONLY the commit message in this exact structure: \n"
                            "<type>(<scope>): <short description>\n"
                            "<optional one extra short line>\n\n"
                            "- <bullet 1>\n- <bullet 2>\n- <bullet 3> (up to 5)\n"
                            "Types allowed: feat, fix, docs, style, refactor, test, chore."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            text = (resp.choices[0].message.content or "").strip()
            return text
        finally:
            _ = time.time() - start
