"""Member C offline and integration checks. Fake LLM replies are test doubles, never real-call evidence."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import get_cleaning_plan
from src.schema import (
    CLASS_LABELS, CSV_COLUMNS, CleaningPlan, ClassificationResult, DataValidationError,
    LLMReply, PlanValidationError, QualityReport,
)


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def generate_plan(self, summary, *, feedback=None):
        self.calls.append({"summary": summary, "feedback": feedback})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def reply(text):
    return LLMReply(text=text, provider="TEST_DOUBLE_NOT_REAL", model="TEST_DOUBLE_NOT_REAL",
                    parameters={"fixture_only": True})


def valid_text():
    return json.dumps({
        "numeric_imputation": "median",
        "categorical_imputation": "constant",
        "categorical_fill_value": "Unknown",
        "reason_numeric": "Robust to outliers in the training data.",
        "reason_categorical": "Explicit missing-category marker.",
    })


def load_report():
    return QualityReport.model_validate_json((ROOT / "examples/quality_report_example.json").read_text(encoding="utf-8"))


def row(i, income="<=50K"):
    values = {
        "age": str(25 + i), "workclass": "Private", "fnlwgt": str(100000 + i),
        "education": "HS-grad", "education_num": "9", "marital_status": "Never-married",
        "occupation": "Sales", "relationship": "Not-in-family", "race": "White",
        "sex": "Male", "capital_gain": "0", "capital_loss": "0",
        "hours_per_week": "40", "native_country": "United-States", "income": income,
        "_source_id": f"src-{i}", "_group_id": f"group-{i}",
    }
    return {k: values[k] for k in CSV_COLUMNS}


class AgentChecks(unittest.TestCase):
    def test_rules_are_offline_and_valid(self):
        class MustNotCall:
            def generate_plan(self, *args, **kwargs):
                raise AssertionError("rules mode must not call model")
        plan = get_cleaning_plan(load_report(), mode="rules", llm_client=MustNotCall())
        self.assertEqual(plan.mode, "rules")
        self.assertEqual(plan.numeric_imputation, "median")
        self.assertEqual(plan.steps, ("normalize_format", "drop_duplicates", "mark_invalid", "impute_missing"))

    def test_only_precleaning_training_report_accepted(self):
        report = load_report()
        with self.assertRaises(DataValidationError):
            get_cleaning_plan(report.model_copy(update={"dataset": "test"}), mode="rules")
        with self.assertRaises(DataValidationError):
            get_cleaning_plan(report.model_copy(update={"stage": "after"}), mode="rules")

    def test_llm_plan_uses_local_mode_and_whitelisted_fields(self):
        client = FakeClient([reply(valid_text())])
        plan = get_cleaning_plan(load_report(), mode="llm", llm_client=client)
        self.assertEqual(plan.mode, "llm")
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn("test_report", json.dumps(client.calls[0]["summary"]))

    def test_invalid_json_gets_exactly_one_correction_attempt(self):
        client = FakeClient([reply("{bad json"), reply(valid_text())])
        events = []
        plan = get_cleaning_plan(load_report(), mode="llm", llm_client=client,
                                 event_sink=lambda n, d: events.append((n, d)))
        self.assertEqual(plan.mode, "llm")
        self.assertEqual(len(client.calls), 2)
        self.assertIsNotNone(client.calls[1]["feedback"])
        self.assertTrue(any(n == "llm_plan_rejected" for n, _ in events))

    def test_bad_plan_after_two_attempts_fails_and_logs(self):
        client = FakeClient([reply("{bad"), reply(valid_text()[:-1] + ',"extra":1}')])
        events = []
        with self.assertRaises(PlanValidationError):
            get_cleaning_plan(load_report(), mode="llm", llm_client=client,
                              event_sink=lambda n, d: events.append((n, d)))
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(sum(n == "llm_plan_rejected" for n, _ in events), 2)

    def test_llm_requires_explicit_client(self):
        with self.assertRaises(Exception):
            get_cleaning_plan(load_report(), mode="llm")


class PipelineChecks(unittest.TestCase):
    def test_pipeline_wires_available_real_collaborators(self):
        # Doubles are permitted only for collaborators whose files do not exist.
        import pandas as pd
        from src import pipeline
        from src.schema import CleaningAudit, CleaningState, CONTRACT_VERSION

        fake_profiler = types.ModuleType("src.profiler")
        def profile_data(df, *, dataset="train", stage="before"):
            return QualityReport(
                dataset=dataset, stage=stage, row_count=len(df), feature_count=14,
                dtypes={c: str(df[c].dtype) for c in df.columns[:14]},
                missing_by_column={c: 0 for c in df.columns[:14]},
                numeric_summary={c: {"count": float(len(df)), "mean": 30.0, "median": 30.0,
                                     "min": 20.0, "max": 50.0, "std": 1.0}
                                 for c in ("age", "fnlwgt", "education_num", "capital_gain", "capital_loss", "hours_per_week")},
            )
        fake_profiler.profile_data = profile_data
        fake_classifier = types.ModuleType("src.classifier")
        def train_and_evaluate(clean_train, clean_test, *, output_dir, seed=42):
            matrix_path = Path(output_dir) / "confusion_matrix.svg"
            matrix_path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
            return ClassificationResult(
                accuracy=0.5, macro_f1=0.5, test_rows=len(clean_test),
                class_counts_test={label: sum(clean_test["income"] == label) for label in CLASS_LABELS},
                confusion_matrix=[
                    [sum((clean_test["income"] == CLASS_LABELS[0])), 0],
                    [sum((clean_test["income"] == CLASS_LABELS[1])), 0],
                ],
                confusion_matrix_path=str(matrix_path),
            )
        fake_classifier.train_and_evaluate = train_and_evaluate
        old_profiler = sys.modules.get("src.profiler")
        old_classifier = sys.modules.get("src.classifier")
        if not (ROOT / "src/profiler.py").is_file():
            sys.modules["src.profiler"] = fake_profiler
        if not (ROOT / "src/classifier.py").is_file():
            sys.modules["src.classifier"] = fake_classifier
        try:
            with tempfile.TemporaryDirectory(prefix="check-c-") as tmp:
                train_path, test_path = Path(tmp)/"train.csv", Path(tmp)/"test.csv"
                pd.DataFrame([row(i, CLASS_LABELS[i % 2]) for i in range(8)]).to_csv(train_path, index=False)
                pd.DataFrame([row(i + 20, CLASS_LABELS[i % 2]) for i in range(4)]).to_csv(test_path, index=False)
                result = pipeline.run_pipeline(train_path, test_path, mode="rules", output_dir=Path(tmp)/"runs")
                self.assertEqual(result.status, "succeeded", result.error_message)
                run_dir = Path(result.output_dir)
                self.assertTrue((run_dir/"events.jsonl").is_file())
                self.assertTrue((run_dir/"cleaning_plan.json").is_file())
                self.assertTrue((run_dir/"train_processed.csv").is_file())
                self.assertTrue((run_dir/"test_processed.csv").is_file())
                self.assertEqual(len(pd.read_csv(run_dir/"test_processed.csv")), 4)
                self.assertTrue(run_dir.is_absolute())
                for relative in result.artifacts.values():
                    self.assertFalse(Path(relative).is_absolute())
                    self.assertTrue((run_dir / relative).is_file())
                self.assertEqual(json.loads((run_dir / "quality_after.json").read_text(encoding="utf-8"))["stage"], "after")
        finally:
            if old_profiler is None:
                sys.modules.pop("src.profiler", None)
            else:
                sys.modules["src.profiler"] = old_profiler
            if old_classifier is None:
                sys.modules.pop("src.classifier", None)
            else:
                sys.modules["src.classifier"] = old_classifier

    def test_overlapping_groups_are_rejected_before_model_call(self):
        import pandas as pd
        from src.pipeline import run_pipeline

        class MustNotCall:
            def generate_plan(self, *args, **kwargs):
                raise AssertionError("A leaking split must not reach the model")

        with tempfile.TemporaryDirectory(prefix="check-c-overlap-") as tmp:
            train, test = Path(tmp) / "train.csv", Path(tmp) / "test.csv"
            pd.DataFrame([row(i, CLASS_LABELS[i % 2]) for i in range(8)]).to_csv(train, index=False)
            pd.DataFrame([row(0)]).to_csv(test, index=False)
            result = run_pipeline(train, test, mode="llm", llm_client=MustNotCall(), output_dir=Path(tmp) / "runs")
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.error_code, "invalid_data")
            events = (Path(result.output_dir) / result.artifacts["events"]).read_text(encoding="utf-8")
            self.assertNotIn('"name":"llm_request"', events)

    def test_runtime_prompt_reference_is_project_relative(self):
        from unittest.mock import patch
        from src import pipeline
        with tempfile.TemporaryDirectory(prefix="check-c-ledger-") as tmp:
            root = Path(tmp)
            ledger = root / "ai_usage/C/usage.json"
            ledger.parent.mkdir(parents=True)
            ledger.write_text(json.dumps({"records": []}), encoding="utf-8")
            client = types.SimpleNamespace(model="TEST_DOUBLE_NOT_REAL")
            # Isolated synthetic ledger; no HTTP call and no public runtime evidence.
            with patch.object(pipeline, "__file__", str(root / "src/pipeline.py")):
                pipeline._record_runtime_request(run_id="fixture-test", request_no=1, client=client,
                                                prompt_data={}, outcome="partial")
            record = json.loads(ledger.read_text(encoding="utf-8"))["records"][0]
            reference = record["prompt_files"][0]
            self.assertTrue(reference.startswith("ai_usage/C/prompts/"))
            self.assertTrue((root / reference).is_file())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--integration", action="store_true")
    parser.add_argument("--real-llm", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    if args.integration:
        # Require actual A/B/D modules; no injected collaborators in this process.
        missing = [name for name in ("src.profiler", "src.cleaner", "src.classifier") if not (ROOT / (name.replace(".", "/") + ".py")).is_file()]
        if missing:
            print("Integration dependencies missing: " + ", ".join(missing), file=sys.stderr)
            return 2
        import importlib
        for name in ("src.profiler", "src.cleaner", "src.classifier"):
            importlib.import_module(name)

    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1

    if args.real_llm:
        from src.llm_client import create_llm_client
        from src.agent import get_cleaning_plan
        report = load_report()
        client = create_llm_client()
        if not client.configured:
            print("Real LLM verification blocked: set LLM_API_URL, LLM_API_KEY, LLM_MODEL.", file=sys.stderr)
            return 2
        out_dir = args.report.parent if args.report else ROOT / "outputs" / "real_llm_check"
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_events = []
        plan = get_cleaning_plan(report, mode="llm", llm_client=client,
                                 event_sink=lambda name, data: raw_events.append({"name": name, "data": data}))
        evidence_path = args.report or out_dir / "real_llm_evidence.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps({
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "mode": "llm", "real_request": True, "provider": "openai_compatible",
            "model": client.model, "plan": plan.model_dump(mode="json"),
            "events": raw_events, "calls_made": client.calls_made,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Real LLM evidence written: {evidence_path}")
    elif args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"status": "passed", "fixture_only": True}, indent=2), encoding="utf-8")

    # Emit a small, sanitized member receipt for the default offline fixture run only.
    if not args.integration and not args.real_llm:
        receipt = {
            "workflow_version": "2.0", "contract_version": "1.0", "role": "C",
            "scope": "fixtures", "status": "passed",
            "checked_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "command": "python checks/check_C.py",
            "summary": {"unit_tests": result.testsRun, "rules_mode": "passed",
                        "plan_validation": "passed", "retry_budget": "at_most_two",
                        "pipeline": "passed_with_A_and_D_test_doubles"},
            "uses_test_doubles": True,
            "artifacts": [],
        }
        (ROOT / "evidence/C").mkdir(parents=True, exist_ok=True)
        (ROOT / "evidence/C/fixtures_check.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
