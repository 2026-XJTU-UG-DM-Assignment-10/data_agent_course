"""Single orchestration path for data profiling, plan selection, cleaning and classification."""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .schema import (
    CSV_COLUMNS, CONTRACT_VERSION, DataValidationError, RunEvent, RunResult,
)
from .agent import get_cleaning_plan
from .llm_client import create_llm_client


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def _read_table(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if not frame.columns.is_unique:
        raise DataValidationError(f"Duplicate CSV headers in {path}")
    missing = [column for column in CSV_COLUMNS if column not in frame.columns]
    extra = [column for column in frame.columns if column not in CSV_COLUMNS]
    if missing or extra:
        raise DataValidationError(f"CSV schema mismatch for {path}; missing={missing}, extra={extra}")
    return frame.loc[:, list(CSV_COLUMNS)]


def run_pipeline(
    train_path: str | Path, test_path: str | Path, *,
    mode: str, output_dir: str | Path = "outputs", seed: int = 42,
    llm_client: Any = None,
) -> RunResult:
    """Execute one run and persist events, raw model exchanges, reports and data exports.

    Model mode never silently falls back to rules. Any exception becomes a failed RunResult;
    detailed exceptions are written locally to the run event log, with secrets excluded.
    """
    if mode not in ("rules", "llm"):
        raise DataValidationError("mode must be 'rules' or 'llm'")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    base = Path(output_dir)
    run_dir = base / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    events_path = run_dir / "events.jsonl"
    sequence = 0
    start = time.monotonic()
    request_counter = 0
    runtime_record_ids: dict[int, str] = {}

    def emit(name: str, data: dict[str, Any] | None = None, status: str = "info") -> None:
        nonlocal sequence
        sequence += 1
        event = RunEvent(
            run_id=run_id, sequence=sequence, mode=mode, name=name, status=status,
            duration_ms=round((time.monotonic() - start) * 1000, 3),
            data=data or {},
        )
        with events_path.open("a", encoding="utf-8") as stream:
            stream.write(event.model_dump_json() + "\n")

    def agent_sink(name: str, data: dict[str, Any]) -> None:
        nonlocal request_counter
        if name == "llm_request_started":
            request_counter += 1
            # Original prompt summary/feedback is retained in local event logs for traceability.
            emit(name, {"request_no": request_counter, **data}, "started")
            # Only the production client creates runtime ledger entries; fake clients never do.
            from .llm_client import LLMClient
            if isinstance(llm_client, LLMClient):
                _record_runtime_request(
                    run_id=run_id, request_no=request_counter, client=llm_client,
                    prompt_data=data, outcome="partial",
                )
                runtime_record_ids[request_counter] = f"{run_id}:{request_counter}"
        else:
            emit(name, data, "failed" if "failed" in name or "rejected" in name else "succeeded")
            if name == "llm_response" and data.get("attempt") in runtime_record_ids:
                _finish_runtime_request(runtime_record_ids[data["attempt"]], data, failed=False)
            elif name == "llm_request_failed" and data.get("attempt") in runtime_record_ids:
                _finish_runtime_request(runtime_record_ids[data["attempt"]], data, failed=True)

    emit("pipeline_started", {"train_path": str(train_path), "test_path": str(test_path), "seed": seed}, "started")
    try:
        train = _read_table(train_path)
        test = _read_table(test_path)
        emit("input_loaded", {"train_rows": len(train), "test_rows": len(test)})
        # Import collaborators at execution time so a missing implementation is explicit.
        from .profiler import profile_data
        from .cleaner import clean_training_data, transform_test_data
        from .classifier import train_and_evaluate

        train_report = profile_data(train, dataset="train", stage="before")
        test_report = profile_data(test, dataset="test", stage="before")
        _write_json(run_dir / "quality_report_train_before.json", train_report)
        _write_json(run_dir / "quality_report_test_before.json", test_report)
        emit("quality_reports_created", {
            "train_report": train_report.model_dump(mode="json"),
            "test_report": test_report.model_dump(mode="json"),
        })
        if mode == "llm" and llm_client is None:
            llm_client = create_llm_client()
        if mode == "llm" and hasattr(llm_client, "configured") and not llm_client.configured:
            from .schema import ModelCallError
            raise ModelCallError("LLM is not configured; set LLM_API_URL, LLM_API_KEY, and LLM_MODEL")
        plan = get_cleaning_plan(train_report, mode=mode, llm_client=llm_client, event_sink=agent_sink)
        _write_json(run_dir / "cleaning_plan.json", plan)
        clean_train, state, train_audit = clean_training_data(train, plan)
        clean_test, test_audit = transform_test_data(test, state)
        _write_json(run_dir / "cleaning_state.json", state)
        _write_json(run_dir / "cleaning_audit_train.json", train_audit)
        _write_json(run_dir / "cleaning_audit_test.json", test_audit)
        clean_train.to_csv(run_dir / "clean_train.csv", index=False, encoding="utf-8")
        clean_test.to_csv(run_dir / "clean_test.csv", index=False, encoding="utf-8")
        emit("cleaning_completed", {
            "train_audit": train_audit.model_dump(mode="json"),
            "test_audit": test_audit.model_dump(mode="json"),
            "clean_train_rows": len(clean_train), "clean_test_rows": len(clean_test),
        }, "succeeded")
        metrics = train_and_evaluate(clean_train, clean_test, output_dir=run_dir, seed=seed)
        result = RunResult(
            contract_version=CONTRACT_VERSION, run_id=run_id, status="succeeded", mode=mode,
            output_dir=str(run_dir),
            artifacts={
                "events": str(events_path),
                "plan": str(run_dir / "cleaning_plan.json"),
                "clean_train": str(run_dir / "clean_train.csv"),
                "clean_test": str(run_dir / "clean_test.csv"),
                "cleaning_state": str(run_dir / "cleaning_state.json"),
                "train_audit": str(run_dir / "cleaning_audit_train.json"),
                "test_audit": str(run_dir / "cleaning_audit_test.json"),
                "confusion_matrix": metrics.confusion_matrix_path,
            },
            metrics=metrics,
        )
        _write_json(run_dir / "run_result.json", result)
        emit("pipeline_completed", {"status": "succeeded", "metrics": metrics.model_dump(mode="json")}, "succeeded")
        return result
    except Exception as exc:
        # Avoid dumping request headers or provider bodies, which may contain credentials.
        error_code = getattr(exc, "code", "pipeline_error")
        message = f"{type(exc).__name__}: {str(exc)[:1000]}"
        try:
            emit("pipeline_failed", {"error_code": error_code, "error_type": type(exc).__name__, "message": message}, "failed")
        except Exception:
            pass
        result = RunResult(
            contract_version=CONTRACT_VERSION, run_id=run_id, status="failed", mode=mode,
            output_dir=str(run_dir), artifacts={"events": str(events_path)},
            error_code=str(error_code), error_message=message,
        )
        _write_json(run_dir / "run_result.json", result)
        return result


def _write_json(path: Path, value: Any) -> None:
    if hasattr(value, "model_dump"):
        content = value.model_dump(mode="json")
    else:
        content = value
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")


def _record_runtime_request(*, run_id: str, request_no: int, client: Any,
                            prompt_data: dict[str, Any], outcome: str) -> None:
    """Persist one actual production-client request attempt and its prompt transcript."""
    project_root = Path(__file__).resolve().parents[1]
    ledger_path = project_root / "ai_usage/C/usage.json"
    if not ledger_path.is_file():
        return
    document = json.loads(ledger_path.read_text(encoding="utf-8"))
    source_id = f"{run_id}:{request_no}"
    if any(item.get("source_id") == source_id for item in document.get("records", [])):
        return
    moment = datetime.now().astimezone()
    prompt_name = f"runtime-{run_id}-{request_no}.md"
    prompt_path = project_root / "ai_usage/C/prompts" / prompt_name
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_text = (
        f"# Project runtime prompt transcript\n\n"
        f"Run: `{run_id}`; request attempt: {request_no}\n\n"
        "## System prompt\n\n"
        + str(prompt_data.get("system_prompt", ""))
        + "\n\n## User payload\n\n```json\n"
        + json.dumps(prompt_data.get("user_payload", {}), ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    prompt_text = re.sub(r"(?i)(authorization\s*:\s*bearer\s+)\S+", r"\1[REDACTED]", prompt_text)
    prompt_path.write_text(prompt_text, encoding="utf-8")
    record = {
        "id": f"C-{moment.strftime('%Y%m%d')}-runtime-{run_id[-8:]}-{request_no}",
        "scope": "project_runtime", "time": moment.isoformat(),
        "tool": "OpenAI-compatible API via requests", "model": client.model or None,
        "parameters": {"temperature": 0, "endpoint_kind": "chat_completions"},
        "parameters_note": "The client sends temperature=0; provider-specific hidden parameters are not assumed.",
        "prompt_files": [str(prompt_path).replace("\\", "/")],
        "calls": 1, "interactions": None, "input_tokens": None, "output_tokens": None,
        "cost": {"kind": "unknown", "amount": None, "currency": None,
                 "basis": "Provider did not expose a verifiable per-request cost."},
        "result": outcome, "source_id": source_id,
        "notes": "One actual production-client HTTP attempt; raw response and execution events are in outputs/<run_id>/events.jsonl.",
    }
    document.setdefault("records", []).append(record)
    ledger_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _finish_runtime_request(source_id: str, response_data: dict[str, Any], *, failed: bool) -> None:
    project_root = Path(__file__).resolve().parents[1]
    ledger_path = project_root / "ai_usage/C/usage.json"
    if not ledger_path.is_file():
        return
    document = json.loads(ledger_path.read_text(encoding="utf-8"))
    for item in document.get("records", []):
        if item.get("scope") == "project_runtime" and item.get("source_id") == source_id:
            item["result"] = "failed" if failed else "succeeded"
            if not failed:
                item["model"] = response_data.get("model") or item.get("model")
                item["input_tokens"] = response_data.get("input_tokens")
                item["output_tokens"] = response_data.get("output_tokens")
                cost = response_data.get("cost")
                currency = response_data.get("currency")
                if cost is not None and currency:
                    item["cost"] = {"kind": "actual", "amount": cost, "currency": currency,
                                    "basis": response_data.get("cost_source") or "Provider-reported request cost."}
            else:
                item["notes"] = item["notes"] + " HTTP/provider request failed; failure detail is in run events."
            break
    ledger_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
