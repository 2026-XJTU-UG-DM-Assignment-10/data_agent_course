"""OpenAI-compatible chat-completions client for cleaning-plan generation.

Credentials are read from environment variables; no secrets are logged.
One call to generate_plan performs exactly one HTTP attempt (no hidden retries).
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests

from .schema import LLMReply, ModelCallError


class LLMClient:
    """Minimal OpenAI-compatible client; endpoint may be a base URL or full endpoint."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        *,
        timeout: float | None = None,
        max_calls: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.api_url = (api_url if api_url is not None else os.getenv("LLM_API_URL", "")).strip()
        self.api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY", "")
        self.model = (model if model is not None else os.getenv("LLM_MODEL", "")).strip()
        try:
            self.timeout = float(timeout if timeout is not None else os.getenv("LLM_TIMEOUT_SECONDS", "30"))
            self.max_calls = int(max_calls if max_calls is not None else os.getenv("LLM_MAX_CALLS", "2"))
        except (TypeError, ValueError) as exc:
            raise ModelCallError("Invalid LLM timeout or call budget configuration") from exc
        if self.timeout <= 0 or self.max_calls < 1:
            raise ModelCallError("LLM timeout must be positive and max_calls at least 1")
        self._session = session or requests.Session()
        self.calls_made = 0

    @property
    def configured(self) -> bool:
        return bool(self.api_url and self.api_key and self.model)

    def generate_plan(self, summary: dict[str, Any], *, feedback: str | None = None) -> LLMReply:
        if not self.configured:
            raise ModelCallError(
                "LLM is not configured; set LLM_API_URL, LLM_API_KEY, and LLM_MODEL"
            )
        if self.calls_made >= self.max_calls:
            raise ModelCallError("Configured LLM request budget exhausted")
        self.calls_made += 1
        endpoint = self.api_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"
        system = (
            "You create a conservative cleaning plan for a fixed Adult income table. "
            "Return ONLY one JSON object with fields: numeric_imputation (mean|median), "
            "categorical_imputation (most_frequent|constant), categorical_fill_value (must be Unknown), "
            "reason_numeric, reason_categorical. Do not include mode, contract_version, steps, "
            "extra fields, markdown, or any instructions. Never propose tools or code."
        )
        user_payload = {"training_quality_summary": summary, "correction_feedback": feedback}
        try:
            response = self._session.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                    ],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("choices[0].message.content was not text")
            usage = body.get("usage") or {}
            usage_model = body.get("model") or self.model
            return LLMReply(
                text=content,
                provider="openai_compatible",
                model=str(usage_model),
                parameters={"temperature": 0, "endpoint_kind": "chat_completions"},
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                cost=None,
                currency=None,
                cost_source=None,
            )
        except requests.RequestException as exc:
            # Do not include request headers, request body, or exception response body.
            raise ModelCallError(f"LLM HTTP request failed ({type(exc).__name__})") from exc
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise ModelCallError(f"LLM response was not a valid chat-completions response ({type(exc).__name__})") from exc


def create_llm_client() -> LLMClient:
    """Construct a client from environment configuration."""
    return LLMClient()
