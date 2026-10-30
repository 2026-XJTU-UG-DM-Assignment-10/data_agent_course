"""Execute the real pipeline against formal data; never substitute fixtures."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.schema import (  # noqa: E402
    CATEGORICAL_COLUMNS, CSV_COLUMNS, METADATA_COLUMNS, TARGET_COLUMN,
    ClassificationResult, CleaningAudit, CleaningPlan, CleaningState, LLMReply,
    QualityReport, RunEvent, RunResult,
)

FORMAL_FILES = (
    "data/raw/adult.data", "data/reference/train_reference.csv",
    "data/reference/test_reference.csv", "data/dirty/train_dirty.csv",
    "data/manifests/split_manifest.csv", "data/manifests/injection_manifest.csv",
    "data/manifests/preparation_summary.json",
)
MODULES = ("src.normalization", "src.profiler", "src.cleaner", "src.agent",
           "src.classifier", "src.pipeline", "src.llm_client")
EXPORTS = {
    "quality_before": QualityReport, "quality_after": QualityReport,
    "cleaning_plan": CleaningPlan, "cleaning_state": CleaningState,
    "metrics": ClassificationResult, "audit_train": CleaningAudit,
    "audit_test": CleaningAudit, "run_result": RunResult,
}


def require(condition, message):
    if not condition:
        raise SmokeCheckError(message)


class SmokeCheckError(ValueError):
    """A controlled diagnostic suitable for the public smoke report."""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(result, key):
    relative = result.artifacts.get(key)
    require(bool(relative) and not Path(relative).is_absolute(), f"Missing relative artifact: {key}")
    root = Path(result.output_dir).resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root) and path.is_file(), f"Invalid/missing artifact: {key}")
    return path


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def verify_events(path, result):
    events = [RunEvent.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(bool(events), "Event log is empty")
    require([e.sequence for e in events] == list(range(1, len(events) + 1)), "Event sequence is not continuous")
    require(all(e.run_id == result.run_id and e.mode == result.mode and e.timestamp.tzinfo
                for e in events), "Event identity/mode/timezone mismatch")
    for name in ("profile", "clean_train", "transform_test", "train_evaluate", "export"):
        require(any(e.name == name and e.status == "succeeded" for e in events), f"No successful {name} event")
    requests = [e for e in events if e.name == "llm_request"]
    if result.mode == "rules":
        require(not requests, "Rules mode created LLM request events")
        return False
    attempts = [e for e in requests if e.status == "started"]
    successes = [e for e in requests if e.status == "succeeded"]
    require(1 <= len(attempts) <= 2 and bool(successes), "Need 1–2 real request attempts and a successful reply")
    payloads = [item for event in requests for item in walk(event.data) if isinstance(item, dict)]
    replies = [LLMReply.model_validate(item) for item in payloads
               if {"text", "provider", "model"} <= item.keys()]
    require(any(reply.text.strip() and reply.model.strip() and reply.provider.strip()
                and "TEST_DOUBLE" not in reply.model.upper() for reply in replies),
            "Need actual LLMReply text/model/provider/parameters in request logs")
    require(any(any(item.get(key) for key in ("prompt", "prompts", "messages")) for item in payloads),
            "No actual prompt/messages in request logs")
    return True


def execute(mode, report):
    import pandas as pd

    missing = [name for name in FORMAL_FILES if not (ROOT / name).is_file()]
    missing += [name for name in MODULES if not (ROOT / (name.replace(".", "/") + ".py")).is_file()]
    if missing:
        report["errors"] = [f"Missing prerequisite: {name}" for name in missing]
        report["next_commands"] = ["python scripts/prepare_data.py --seed 42 --sample-size 10000",
                                   f"python scripts/smoke_check.py --mode {mode} --report outputs/integration/smoke_{mode}.json"]
        return 2
    # Import errors in present modules are failures, never grounds to inject doubles.
    modules = {name: importlib.import_module(name) for name in MODULES}
    require(all(Path(module.__file__).resolve() == ROOT / (name.replace(".", "/") + ".py")
                for name, module in modules.items()), "Non-project module loaded")
    report["modules"] = list(modules)
    before_hashes = {name: digest(ROOT / name) for name in FORMAL_FILES}
    frames = {name: pd.read_csv(ROOT / name, dtype=str, keep_default_na=False)
              for name in FORMAL_FILES if name.endswith(".csv")}
    train = frames["data/dirty/train_dirty.csv"]
    reference = frames["data/reference/train_reference.csv"]
    test = frames["data/reference/test_reference.csv"]
    for name, frame in (("train", train), ("reference", reference), ("test", test)):
        require(tuple(frame.columns) == CSV_COLUMNS and not frame.empty, f"Invalid formal {name} schema")
    require(len(reference) >= 5000 and len(train) >= 5000, "Formal training inputs must have at least 5,000 rows")
    require(not set(train._group_id) & set(test._group_id), "Train/test groups overlap")
    require(set(zip(train._source_id, train._group_id)) <= set(zip(reference._source_id, reference._group_id)),
            "Dirty records lost reference provenance")
    split = frames["data/manifests/split_manifest.csv"]
    require({"_source_id", "_group_id", "split"} <= set(split.columns), "Split manifest columns missing")
    require(set(split.split) == {"train", "test"}, "Invalid split names")
    for expected, frame in (("train", reference), ("test", test)):
        recorded = split[split.split == expected]
        require(set(zip(recorded._source_id, recorded._group_id)) == set(zip(frame._source_id, frame._group_id)),
                f"Split manifest disagrees with {expected}")
    require(not frames["data/manifests/injection_manifest.csv"].empty, "Empty injection manifest")
    require(bool(json.loads((ROOT / "data/manifests/preparation_summary.json").read_text(encoding="utf-8"))),
            "Empty preparation summary")
    profiler = modules["src.profiler"].profile_data
    before = profiler(train, dataset="train", stage="before")
    require(all(value > 0 for value in (sum(before.missing_by_column.values()), before.duplicate_rows,
                                        before.outlier_cells, before.format_issue_cells)),
            "Formal training data does not exhibit all four quality issues")
    if mode == "llm":
        import os
        if not all(os.environ.get(name, "").strip() for name in ("LLM_API_URL", "LLM_API_KEY", "LLM_MODEL")):
            report["errors"].append("Real model configuration is missing (environment values are not logged)")
            return 2
    result = modules["src.pipeline"].run_pipeline(
        ROOT / "data/dirty/train_dirty.csv", ROOT / "data/reference/test_reference.csv",
        mode=mode, output_dir=ROOT / "outputs" / "smoke_runs", seed=42,
    )
    result = RunResult.model_validate(result)
    report["run_id"] = result.run_id
    run_dir = Path(result.output_dir).resolve()
    require(run_dir.is_relative_to(ROOT / "outputs") and run_dir.is_dir(), "Run directory must be inside outputs")
    report["evidence"].extend(path.relative_to(ROOT).as_posix() for path in run_dir.rglob("*") if path.is_file())
    require(result.status == "succeeded", f"Pipeline failed: {result.error_code}")
    require(result.mode == mode, "Pipeline silently changed modes")
    report["uses_real_modules"] = True
    exports = {key: schema.model_validate_json(artifact(result, key).read_text(encoding="utf-8"))
               for key, schema in EXPORTS.items()}
    require(exports["run_result"] == result, "Exported RunResult differs from returned result")
    require(exports["metrics"] == result.metrics, "Exported metrics differ from returned metrics")
    require(exports["cleaning_plan"].mode == mode, "Exported plan mode differs")
    require(artifact(result, "summary").stat().st_size > 0, "Empty summary")
    require(artifact(result, "confusion_matrix").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "Invalid confusion matrix PNG")
    text_columns = {column: str for column in CATEGORICAL_COLUMNS + METADATA_COLUMNS + (TARGET_COLUMN,)}
    processed_train = pd.read_csv(artifact(result, "train_processed"), dtype=text_columns, keep_default_na=False)
    processed_test = pd.read_csv(artifact(result, "test_processed"), dtype=text_columns, keep_default_na=False)
    # Reuse D's clean-input boundary; it does not clean or fit any parameters.
    validate = modules["src.classifier"]._validate_clean_frame
    validate(processed_train, "train")
    validate(processed_test, "test")
    require(len(processed_train) >= 5000, "Processed training data has fewer than 5,000 rows")
    require(tuple(processed_train.columns) == CSV_COLUMNS and tuple(processed_test.columns) == CSV_COLUMNS,
            "Processed CSV schema differs")
    require(not set(processed_train._group_id) & set(processed_test._group_id), "Processed source groups overlap")
    keys = [TARGET_COLUMN, *METADATA_COLUMNS]
    pd.testing.assert_frame_equal(test[keys].reset_index(drop=True),
                                  processed_test[keys].reset_index(drop=True), check_dtype=False)
    require(result.metrics.test_rows == len(test), "Metrics test row count differs")
    after = profiler(processed_train, dataset="train", stage="after")
    require(all(value == 0 for value in (sum(after.missing_by_column.values()), after.duplicate_rows,
                                         after.outlier_cells, after.format_issue_cells)), "Quality issues remain")
    require(exports["quality_before"] == before and exports["quality_after"] == after,
            "Exported profiles differ from direct profiling")
    for kind, raw, clean in (("train", train, processed_train), ("test", test, processed_test)):
        audit = exports[f"audit_{kind}"]
        require(audit.dataset == kind and audit.input_rows == len(raw) and audit.output_rows == len(clean),
                f"{kind} audit row counts differ")
    report["real_llm_checked"] = verify_events(artifact(result, "events"), result)
    require(before_hashes == {name: digest(ROOT / name) for name in FORMAL_FILES}, "Formal input files changed")
    report["formal_data_checked"] = True
    report["evidence"].extend(name for name in FORMAL_FILES if name.startswith("data/manifests/"))
    report["summary"] = {"train_before": len(train), "train_after": len(processed_train),
                         "test_rows": len(test), "accuracy": result.metrics.accuracy,
                         "macro_f1": result.metrics.macro_f1, "input_sha256": before_hashes}
    report["status"] = "passed"
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("rules", "llm"), default="rules")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.report is None:
        args.report = ROOT / f"outputs/integration/smoke_{args.mode}.json"
    report = {"status": "not_ready", "mode": args.mode, "uses_real_modules": False,
              "formal_data_checked": False, "real_llm_checked": False, "evidence": [],
              "checked_at": datetime.now(timezone.utc).isoformat(), "errors": []}
    try:
        code = execute(args.mode, report)
    except Exception as exc:
        report["status"] = "failed"
        # Do not serialize arbitrary upstream exception messages or credentials.
        report["errors"].append(str(exc) if isinstance(exc, SmokeCheckError) else type(exc).__name__)
        code = 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
