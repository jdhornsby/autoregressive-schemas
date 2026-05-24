"""Calls the generator model (Gemini via Vertex AI) with forced structured output."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Type

from google import genai
from google.genai.types import GenerateContentConfig, ThinkingConfig
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

THINKING_LEVELS = ("minimal", "low", "medium", "high")

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=os.environ["GCP_PROJECT"],
            location=os.environ.get("GCP_LOCATION", "global"),
        )
    return _client


@retry(wait=wait_exponential(multiplier=1, min=4, max=120), stop=stop_after_attempt(10))
def _call_model(
    schema: Type[BaseModel],
    filled: str,
    model_name: str,
    thinking_config: ThinkingConfig | None,
) -> tuple[BaseModel, dict[str, Any]]:
    """Single generation attempt (tenacity handles retries)."""
    client = _get_client()

    config = GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=1.0,
        thinking_config=thinking_config,
    )

    t0 = time.monotonic()
    response = client.models.generate_content(
        model=model_name,
        contents=filled,
        config=config,
    )
    latency_ms = round((time.monotonic() - t0) * 1000)

    usage = response.usage_metadata
    stats = {
        "latency_ms": latency_ms,
        "thinking_level": None,
        "prompt_tokens": getattr(usage, "prompt_token_count", 0) or 0,
        "thinking_tokens": getattr(usage, "thoughts_token_count", 0) or 0,
        "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
    }
    return schema.model_validate_json(response.text), stats


def generate(
    schema: Type[BaseModel],
    prompt: str,
    *,
    thinking_level: str | None = None,
    model: str | None = None,
    **template_vars: Any,
) -> tuple[BaseModel, dict[str, Any]]:
    """Fill the prompt template and call the generator. Returns (result, stats)."""
    filled = prompt.format(**template_vars)
    model_name = model or os.environ.get("GENERATOR_MODEL", DEFAULT_MODEL)

    thinking_config = None
    if thinking_level is not None:
        thinking_config = ThinkingConfig(thinking_level=thinking_level.upper())

    _call_model.statistics.clear()
    result, stats = _call_model(schema, filled, model_name, thinking_config)

    stats["retries"] = _call_model.statistics.get("attempt_number", 1) - 1
    stats["thinking_level"] = thinking_level
    stats["model"] = model_name

    return result, stats
