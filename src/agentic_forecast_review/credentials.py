"""OpenRouter API key lookup: environment first, then the ignored repo-root .env."""

from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "OPENROUTER_API_KEY"
PLACEHOLDER_KEY = "replace_with_your_openrouter_api_key"


def openrouter_api_key() -> str:
    key = os.environ.get(ENV_VAR, "").strip()
    if key and key != PLACEHOLDER_KEY:
        return key
    env_path = Path.cwd() / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.strip().partition("=")
            if name == ENV_VAR and separator:
                key = value.strip()
                break
    if not key or key == PLACEHOLDER_KEY:
        raise RuntimeError(
            "OpenRouter API key is missing or a placeholder; set OPENROUTER_API_KEY."
        )
    return key
