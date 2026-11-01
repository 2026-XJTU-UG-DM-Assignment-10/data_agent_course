"""D's real classifier, Streamlit interaction and CLI checks.

Only the absent C pipeline may be replaced for offline UI/CLI interaction tests.
Integration mode never installs that replacement and never rewrites receipts.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import types
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "outputs/member_D"
(OUTPUT / "tmp").mkdir(parents=True, exist_ok=True)
# Keep Streamlit's temporary directories within the writable project workspace.
tempfile.tempdir = str(OUTPUT / "tmp")

import numpy as np
import pandas as pd
from PIL import Image
from streamlit.testing.v1 import AppTest

from src import classifier, cli
from src.schema import (
    CLASS_LABELS, FEATURE_COLUMNS, NUMERIC_COLUMNS, CleaningAudit,
    DataValidationError, QualityReport, RunResult,
)

def check(condition, message):
    if not condition:
        raise AssertionError(message)


def classifier_checks(report):
    train = pd.read_csv(ROOT / "examples/clean_train_small.csv")
    test = pd.read_csv(ROOT / "examples/clean_test_small.csv")
    originals = (train.copy(deep=True), test.copy(deep=True))
    captured = []
    builder = classifier._build_model

    def capture(seed):
        model = builder(seed)
        captured.append(model)
        return model

    with patch.object(classifier, "_build_model", side_effect=capture):
        metrics = classifier.train_and_evaluate(train, test, output_dir=OUTPUT / "classification")
    pd.testing.assert_frame_equal(train, originals[0])
    pd.testing.assert_frame_equal(test, originals[1])
    model = captured[0]
    preprocessing = model.named_steps["preprocessing"]
    check(tuple(preprocessing.feature_names_in_) == FEATURE_COLUMNS, "IDs/label/extra columns entered features")
    np.testing.assert_allclose(preprocessing.named_transformers_["numeric"].mean_,
                               train.loc[:, list(NUMERIC_COLUMNS)].mean().to_numpy())
    encoder = preprocessing.named_transformers_["categorical"]
    check("Unseen-example-workclass" not in encoder.categories_[0], "Encoder fitted on test categories")
    check(encoder.handle_unknown == "ignore", "Unknown categories not supported")
    predictions = model.predict(test.loc[:, list(FEATURE_COLUMNS)])
    independent_matrix = [[sum((test.income.to_numpy() == actual) & (predictions == predicted))
                           for predicted in CLASS_LABELS] for actual in CLASS_LABELS]
    check(metrics.confusion_matrix == independent_matrix, "Matrix orientation/label order mismatch")
    check(metrics.labels == CLASS_LABELS, "Class labels not fixed")
    correct = sum(independent_matrix[i][i] for i in range(2))
    check(metrics.accuracy == correct / len(test), "Accuracy is inconsistent")
    f1s = []
    for index in range(2):
        tp = independent_matrix[index][index]
        denominator = sum(independent_matrix[index]) + sum(row[index] for row in independent_matrix)
        f1s.append(2 * tp / denominator if denominator else 0)
    check(abs(metrics.macro_f1 - sum(f1s) / 2) < 1e-12, "Macro-F1 is inconsistent")
    with Image.open(metrics.confusion_matrix_path) as image:
        image.verify()
    # Metadata and unused extra columns cannot affect the fitted features or predictions.
    changed_train, changed_test = train.copy(), test.copy()
    for frame, prefix in ((changed_train, "train"), (changed_test, "test")):
        frame["_source_id"] = [f"{prefix}-new-source-{i}" for i in range(len(frame))]
        frame["_group_id"] = [f"{prefix}-new-group-{i}" for i in range(len(frame))]
        frame["unused_leaky_copy_of_label"] = frame.income
    changed = classifier.train_and_evaluate(changed_train, changed_test, output_dir=OUTPUT / "metadata")
    check(changed.model_dump(exclude={"confusion_matrix_path"}) == metrics.model_dump(exclude={"confusion_matrix_path"}),
          "Metadata/extra columns affect results")
    one_class_test = test[test.income == ">50K"].copy()
    one_class = classifier.train_and_evaluate(train, one_class_test, output_dir=OUTPUT / "single_test_class")
    check(one_class.class_counts_test["<=50K"] == 0 and len(one_class.confusion_matrix) == 2,
          "Single-class test must retain the 2x2 matrix")
    invalid_cases = []

    def rejects(name, bad_train, bad_test):
        try:
            classifier.train_and_evaluate(bad_train, bad_test, output_dir=OUTPUT / "invalid")
        except DataValidationError:
            invalid_cases.append(name)
        else:
            raise AssertionError(f"Accepted invalid input: {name}")

    rejects("missing_feature", train.drop(columns="age"), test)
    rejects("missing_metadata", train.drop(columns="_source_id"), test)
    rejects("one_training_class", train[train.income == "<=50K"], test)
    rejects("empty_test", train, test.iloc[:0])
    rejects("bad_label", train.assign(income="invalid"), test)
    rejects("missing_category", train.assign(workclass="?"), test)
    rejects("missing_numeric", train.assign(age=np.nan), test)
    rejects("infinite_numeric", train.assign(age=np.inf), test)
    rejects("out_of_range", train.assign(hours_per_week=999), test)
    rejects("nonpositive_weight", train.assign(fnlwgt=0), test)
    rejects("unnormalized_numeric", train.assign(age="40 years"), test)
    rejects("boolean_numeric", train.assign(age=True), test)
    rejects("duplicate_training", pd.concat([train, train.iloc[:1]], ignore_index=True), test)
    rejects("overlapping_groups", train, test.assign(_group_id=train._group_id.iloc[0]))
    duplicate_columns = train.copy()
    duplicate_columns.columns = ["age"] * len(train.columns)
    rejects("duplicate_columns", duplicate_columns, test)
    report["classification"] = {"train_rows": len(train), "test_rows": len(test),
                                "metrics": metrics.model_dump(mode="json"),
                                "checks": ["train_only_scaler_and_encoder", "fixed_14_features", "unknown_category",
                                           "matrix_orientation", "independent_accuracy_and_macro_f1",
                                           "input_immutability", "metadata_exclusion", "single_class_test", "valid_png"],
                                "invalid_inputs_rejected": invalid_cases}
    return metrics


def ui_and_cli_checks(report, metrics, integration):
    exists = importlib.util.find_spec("src.pipeline") is not None
    if integration:
        missing = [name for name in ("normalization", "cleaner", "profiler", "agent", "pipeline", "llm_client")
                   if not (ROOT / f"src/{name}.py").is_file()]
        if missing:
            report["missing_dependencies"] = missing
            return 2
    calls = []
    ui_output = OUTPUT / "ui_test_double"
    ui_output.mkdir(parents=True, exist_ok=True)
    (ui_output / "summary.md").write_text("SYNTHETIC UI TEST DOUBLE — not a real pipeline run\n", encoding="utf-8")
    (ui_output / "events.jsonl").write_text('{"test_double":true}\n', encoding="utf-8")
    (ui_output / "train_processed.csv").write_text("test_double\ntrue\n", encoding="utf-8")
    before = QualityReport.model_validate_json((ROOT / "examples/quality_report_example.json").read_text(encoding="utf-8"))
    after = before.model_copy(update={"stage": "after", "row_count": 7, "duplicate_rows": 0,
                                      "outlier_cells": 0, "format_issue_cells": 0,
                                      "missing_by_column": {key: 0 for key in FEATURE_COLUMNS}})
    (ui_output / "quality_before.json").write_text(before.model_dump_json(), encoding="utf-8")
    (ui_output / "quality_after.json").write_text(after.model_dump_json(), encoding="utf-8")
    (ui_output / "cleaning_plan.json").write_bytes((ROOT / "examples/plan_rules.json").read_bytes())
    audit = CleaningAudit(dataset="train", input_rows=8, output_rows=7,
                          duplicate_rows_removed_before_fill=1, missing_cells_filled=4)
    (ui_output / "audit_train.json").write_text(audit.model_dump_json(), encoding="utf-8")
    fake = types.ModuleType("src.pipeline")

    def fake_run(train_path, test_path, *, mode, output_dir="outputs", seed=42, llm_client=None):
        calls.append({"mode": mode, "train": str(train_path), "test": str(test_path)})
        return RunResult(run_id="D-UI-TEST-DOUBLE", status="succeeded", mode=mode,
                         output_dir=str(ui_output), metrics=metrics,
                         artifacts={"summary": "summary.md", "events": "events.jsonl",
                                    "train_processed": "train_processed.csv", "quality_before": "quality_before.json",
                                    "quality_after": "quality_after.json", "cleaning_plan": "cleaning_plan.json",
                                    "audit_train": "audit_train.json"})

    fake.run_pipeline = fake_run
    # No substitution when the real dependency exists, even if its import fails.
    context = patch.dict(sys.modules, {"src.pipeline": fake}) if not exists else contextlib.nullcontext()
    report["uses_test_doubles"] = not exists
    with context:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(["--train", "examples/train_small.csv", "--test", "examples/test_small.csv", "--mode", "rules"])
        check(code == 0 and json.loads(stdout.getvalue())["status"] == "succeeded", "CLI success path failed")
        result = RunResult.model_validate_json(stdout.getvalue())
        check(result.mode == "rules", "CLI lost requested mode")
        if not exists:
            failed = RunResult(run_id="D-FAILURE-TEST-DOUBLE", status="failed", mode="rules",
                               output_dir=str(ui_output), error_code="controlled_test_failure", error_message="Test only")
            with patch.object(fake, "run_pipeline", return_value=failed):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    check(cli.main(["--train", "examples/train_small.csv", "--test", "examples/test_small.csv"]) == 1,
                          "CLI returned success for failed RunResult")
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        check(not at.exception, "Initial page exception")
        check(len(at.metric) == 0, "Initial page fabricated successful metrics")
        before_calls = len(calls)
        at.checkbox[0].uncheck().run()
        at.text_input[0].set_value(str(ROOT / "examples/train_small.csv"))
        at.text_input[1].set_value(str(ROOT / "examples/test_small.csv"))
        at.button[0].click().run()
        check(not at.exception and len(at.success) == 1 and len(at.metric) == 2, "Page did not display success/metrics")
        if not exists:
            check(len(calls) == before_calls + 1, "One click did not create exactly one request")
            table = at.table[0].value
            check(table["处理前"].tolist() == [before.row_count, sum(before.missing_by_column.values()),
                                             before.duplicate_rows, before.outlier_cells, before.format_issue_cells],
                  "Page before counts differ from exported report")
            check(table["处理后"].tolist() == [7, 0, 0, 0, 0], "Page after counts differ from exported report")
            check(len(at.json) == 1 and len(at.expander) == 1, "Cleaning audit not displayed")
            check(any("数值填补" in item.value for item in at.markdown), "Strategy/reasons not displayed")
        at.run()
        at.selectbox[0].select("llm").run()
        check(not at.exception and len(at.metric) == 2, "Rerun lost the stored result")
        check(any("结果模式：rules" in item.value for item in at.caption), "Old result mislabeled with new selector mode")
        if not exists:
            check(len(calls) == before_calls + 1, "Page redraw/selector called the pipeline")
        check(len(at.get("download_button")) >= 3, "Required download controls missing")
        at.text_input[0].set_value(str(OUTPUT / "does-not-exist.csv"))
        at.button[0].click().run()
        check(not at.exception and len(at.error) > 0 and len(at.metric) == 0, "Failed start kept stale success/metrics")
        if not exists:
            with patch.object(fake, "run_pipeline", return_value=failed):
                at.text_input[0].set_value(str(ROOT / "examples/train_small.csv"))
                at.button[0].click().run()
                check(not at.exception and len(at.error) > 0 and len(at.metric) == 0,
                      "Page failed RunResult displayed metrics")
        preview = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        preview.checkbox[1].check().run()
        check(not preview.exception and len(preview.metric) == 2 and len(preview.warning) > 0,
              "Synthetic preview not labeled/rendered")
    process = subprocess.run([sys.executable, "-m", "src.cli", "--train", "missing-D-check.csv"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    check(process.returncode == 1 and "Input CSV does not exist" in process.stderr, "CLI missing-input exit code/message")
    process = subprocess.run([sys.executable, "-m", "src.cli", "--mode", "invalid"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    check(process.returncode == 2, "CLI invalid arguments should exit 2")
    import app
    unsafe = result.model_copy(update={"artifacts": {"outside": "../../README.md"}})
    check(app.artifact_path(unsafe, "outside") is None, "UI allows artifact directory traversal")
    report["ui_cli"] = {"checks": ["success_and_failed_RunResult" if not exists else "real_rules_pipeline",
                                   "page_redraw_keeps_result", "one_click_one_run", "mode_selection_keeps_result_mode",
                                   "failed_start_clears_metrics", "synthetic_preview_labeled", "downloads_present",
                                   "artifact_path_containment", "cli_missing_input_exit_1", "cli_invalid_mode_exit_2"],
                        "pipeline_calls_under_test_double": len(calls) if not exists else None,
                        "download_click_in_this_command": "not_run; separate manual browser evidence, when available, is in outputs/member_D/browser_check.json"}
    if not exists:
        report["ui_cli"]["checks"].extend(["before_after_quality_table", "strategy_and_reasons", "cleaning_audit"])
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integration", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "scope": "fixtures", "integration": args.integration,
              "uses_test_doubles": False, "checked_at": datetime.now(timezone.utc).isoformat()}
    code = 1
    try:
        metrics = classifier_checks(report)
        code = ui_and_cli_checks(report, metrics, args.integration)
        report["status"] = "passed" if code == 0 else "not_ready"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        import traceback
        traceback.print_exc()
    target = OUTPUT / ("integration_check.json" if args.integration else "check.json")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if code == 0 and not args.integration:
        receipt = {"workflow_version": "2.0", "contract_version": "1.0", "role": "D",
                   "scope": "fixtures", "status": "passed", "checked_at": report["checked_at"],
                   "command": "python checks/check_D.py", "uses_test_doubles": report["uses_test_doubles"],
                   "summary": {"train_rows": report["classification"]["train_rows"],
                               "test_rows": report["classification"]["test_rows"],
                               "accuracy": metrics.accuracy, "macro_f1": metrics.macro_f1,
                               "confusion_matrix": metrics.confusion_matrix,
                               "classification_checks": report["classification"]["checks"],
                               "invalid_inputs_rejected": len(report["classification"]["invalid_inputs_rejected"]),
                               "ui_cli_checks": report["ui_cli"]["checks"],
                               "limitations": "Synthetic 7/3 fixtures; missing C replaced ONLY for UI/CLI; no formal data, real model or end-to-end evidence"},
                   "artifacts": ["outputs/member_D/check.json", "outputs/member_D/classification/confusion_matrix.png"]}
        path = ROOT / "evidence/D/fixtures.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
