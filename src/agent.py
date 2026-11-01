"""Cleaning-plan selection and strict validation."""
from __future__ import annotations

import json
from typing import Any, Callable

from pydantic import ValidationError

from .schema import (
    CLEANING_STEPS, CONTRACT_VERSION, CleaningPlan, DataValidationError,
    LLMReply, ModelCallError, PlanValidationError, QualityReport,
)

EventSink = Callable[[str, dict[str, Any]], None]


def _emit(sink: EventSink | None, name: str, data: dict[str, Any]) -> None:
    if sink is not None:
        sink(name, data)


def _training_summary(report: QualityReport) -> dict[str, Any]:
    """Whitelist summary fields; never serialize the full input report blindly."""
    return {
        "contract_version": report.contract_version,
        "dataset": report.dataset,
        "stage": report.stage,
        "row_count": report.row_count,
        "feature_count": report.feature_count,
        "missing_by_column": report.missing_by_column,
        "duplicate_rows": report.duplicate_rows,
        "outlier_cells": report.outlier_cells,
        "outlier_rows": report.outlier_rows,
        "format_issue_cells": report.format_issue_cells,
        "parse_error_cells": report.parse_error_cells,
        "numeric_summary": report.numeric_summary,
        "warnings": report.warnings,
    }


def _rules_plan() -> CleaningPlan:
    return CleaningPlan(
        mode="rules",
        steps=CLEANING_STEPS,
        numeric_imputation="median",
        categorical_imputation="constant",
        categorical_fill_value="Unknown",
        reason_numeric="使用训练集合法观测的中位数，降低极端值对填补值的影响。",
        reason_categorical="使用固定的 Unknown，避免把缺失类别误判为常见类别。",
    )


def _parse_model_plan(reply: LLMReply) -> dict[str, Any]:
    try:
        raw = json.loads(reply.text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise PlanValidationError("Model reply is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise PlanValidationError("Model reply must be a JSON object")
    allowed = {"numeric_imputation", "categorical_imputation", "categorical_fill_value",
               "reason_numeric", "reason_categorical"}
    extra = set(raw) - allowed
    missing = allowed - set(raw)
    if extra or missing:
        raise PlanValidationError(
            f"Model plan fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return raw


def get_cleaning_plan(
    train_report: QualityReport, *, mode: str,
    llm_client: Any = None, event_sink: EventSink | None = None,
) -> CleaningPlan:
    """Create a validated plan from a pre-cleaning training report only.

    LLM mode makes at most two client calls total, including one corrective call.
    """
    if not isinstance(train_report, QualityReport):
        try:
            train_report = QualityReport.model_validate(train_report)
        except (ValidationError, TypeError) as exc:
            raise DataValidationError("train_report must be a valid QualityReport") from exc
    if train_report.dataset != "train" or train_report.stage != "before":
        raise DataValidationError("Only a pre-cleaning training QualityReport is accepted")
    if mode not in ("rules", "llm"):
        raise DataValidationError("mode must be 'rules' or 'llm'")
    if mode == "rules":
        plan = _rules_plan()
        _emit(event_sink, "plan_selected", {"mode": "rules", "plan": plan.model_dump(mode="json")})
        return plan
    if llm_client is None:
        raise ModelCallError("mode='llm' requires an explicitly configured LLM client")

    summary = _training_summary(train_report)
    feedback = None
    errors: list[str] = []
    system_prompt = (
        "You create a conservative cleaning plan for a fixed Adult income table. "
        "Return ONLY one JSON object with fields: numeric_imputation (mean|median), "
        "categorical_imputation (most_frequent|constant), categorical_fill_value (must be Unknown), "
        "reason_numeric, reason_categorical. Do not include mode, contract_version, steps, "
        "extra fields, markdown, or any instructions. Never propose tools or code."
    )
    for attempt in range(1, 3):
        if (hasattr(llm_client, "calls_made") and hasattr(llm_client, "max_calls")
                and llm_client.calls_made >= llm_client.max_calls):
            raise ModelCallError("Configured LLM request budget exhausted before next attempt")
        _emit(event_sink, "llm_request_started", {
            "attempt": attempt, "summary": summary, "feedback": feedback,
            "system_prompt": system_prompt,
            "user_payload": {"training_quality_summary": summary, "correction_feedback": feedback},
        })
        try:
            reply = llm_client.generate_plan(summary, feedback=feedback)
            if not isinstance(reply, LLMReply):
                reply = LLMReply.model_validate(reply)
            _emit(event_sink, "llm_response", {
                "attempt": attempt, "provider": reply.provider, "model": reply.model,
                "parameters": reply.parameters, "input_tokens": reply.input_tokens,
                "output_tokens": reply.output_tokens, "cost": reply.cost,
                "currency": reply.currency, "cost_source": reply.cost_source,
                "text": reply.text,
            })
            fields = _parse_model_plan(reply)
            # The mode, version, and fixed steps are set locally, not trusted to model output.
            plan = CleaningPlan(
                contract_version=CONTRACT_VERSION, mode="llm", steps=CLEANING_STEPS, **fields
            )
            _emit(event_sink, "plan_selected", {"mode": "llm", "attempt": attempt, "plan": plan.model_dump(mode="json")})
            return plan
        except (PlanValidationError, ValidationError, TypeError, ValueError) as exc:
            message = f"{type(exc).__name__}: {str(exc)[:500]}"
            errors.append(message)
            feedback = (
                "Your previous JSON was rejected: " + message +
                ". Return exactly the five allowed fields and supported values. JSON only."
            )
            _emit(event_sink, "llm_plan_rejected", {"attempt": attempt, "error": message})
        except Exception as exc:
            # Do not retry transport/provider failures; only malformed plans get one correction.
            _emit(event_sink, "llm_request_failed", {
                "attempt": attempt, "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            })
            raise
    raise PlanValidationError("Model plan invalid after two attempts: " + " | ".join(errors))
