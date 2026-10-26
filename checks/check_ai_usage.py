"""AI accounting regression checks. All entries here are isolated synthetic test data."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.summarize_ai_usage import load_records, render_markdown, summarize


class UsageChecks(unittest.TestCase):
    def setUp(self):
        qa = ROOT / "outputs" / "ai_usage_qa"
        qa.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="usage-check-", dir=qa)
        self.root = Path(self.temp.name).resolve()
        assert self.root.parent == qa.resolve() and self.root.is_relative_to(ROOT)
        self.addCleanup(self.temp.cleanup)
        for role in "ABCD":
            folder = self.root / "ai_usage" / role
            (folder / "prompts").mkdir(parents=True)
            (folder / "prompts/test.md").write_text("Synthetic prompt for isolated accounting checks only.", encoding="utf-8")
            self.write(role, [])

    def write(self, role, records):
        document = {"schema_version": "1.0", "role": role, "coverage_note": "Synthetic test data only", "records": records}
        (self.root / "ai_usage" / role / "usage.json").write_text(json.dumps(document), encoding="utf-8")

    def entry(self, role="B", suffix="1"):
        return {"id": f"{role}-{suffix}", "time": "2026-10-26T11:00:00+08:00", "tool": "Synthetic test tool",
                "scope": "development", "source_id": f"synthetic-{role}-{suffix}", "model": "test-model",
                "parameters": {}, "parameters_note": "Not measured; synthetic control input",
                "prompt_files": [f"ai_usage/{role}/prompts/test.md"], "calls": None, "interactions": 2,
                "input_tokens": None, "output_tokens": None,
                "cost": {"kind": "unknown", "amount": None, "currency": None, "basis": "Synthetic unknown"},
                "result": "partial", "notes": "Not a real model call or course experiment"}

    def test_empty_is_valid_foundation_but_not_delivery(self):
        self.assertEqual(load_records(self.root), [])
        with self.assertRaises(ValueError):
            load_records(self.root, "B", require_records=True)

    def test_unknown_counts_do_not_become_total_or_free(self):
        self.write("B", [self.entry()])
        summary = summarize(load_records(self.root))
        self.assertEqual(summary["rows"][0]["unknown_calls_records"], 1)
        self.assertEqual(summary["cost_subtotals"], [])
        self.assertEqual(summary["unknown_cost_records"], {"development": 1})
        self.assertIn("未知", render_markdown(summary))

    def test_actual_estimate_currency_and_scope_are_separate(self):
        items = []
        for suffix, kind, currency, amount in [("1", "actual", "CNY", 0.1), ("2", "actual", "CNY", 0.2),
                                                ("3", "estimate", "CNY", 9), ("4", "actual", "USD", 2)]:
            item = self.entry(suffix=suffix)
            item["calls"] = 1
            item["cost"] = {"kind": kind, "currency": currency, "amount": amount, "basis": "Synthetic known cost"}
            items.append(item)
        self.write("B", items)
        runtime = self.entry("C")
        runtime.update(scope="project_runtime", calls=1, result="failed", source_id="test-run:1")
        self.write("C", [runtime])
        summary = summarize(load_records(self.root))
        self.assertIn({"scope": "development", "kind": "actual", "currency": "CNY", "amount": "0.3"}, summary["cost_subtotals"])
        self.assertEqual(len(summary["cost_subtotals"]), 3)
        self.assertEqual(summary["unknown_cost_records"], {"project_runtime": 1})

    def test_duplicate_source_or_id_is_rejected(self):
        first = self.entry()
        for change in ({"id": "B-2"}, {"source_id": "other-source"}):
            self.write("B", [first, {**first, **change}])
            with self.assertRaises(ValueError):
                load_records(self.root)

    def test_zero_is_allowed_only_with_known_cost_basis(self):
        item = self.entry()
        item["cost"]["amount"] = 0
        self.write("B", [item])
        with self.assertRaises(ValueError):
            load_records(self.root)
        item["cost"].update(kind="actual", currency="CNY")
        self.write("B", [item])
        self.assertEqual(summarize(load_records(self.root))["cost_subtotals"][0]["amount"], "0")

    def test_runtime_has_one_owner_and_one_attempt_per_record(self):
        item = self.entry()
        item.update(scope="project_runtime", calls=1)
        self.write("B", [item])
        with self.assertRaises(ValueError):
            load_records(self.root)
        self.write("B", [])
        item = self.entry("C")
        item.update(scope="project_runtime", calls=2)
        self.write("C", [item])
        with self.assertRaises(ValueError):
            load_records(self.root)

    def test_unsafe_missing_and_cross_member_prompts_are_rejected(self):
        for reference in ["ai_usage/B/prompts/../../outside.md", "ai_usage/B/prompts/missing.md", "ai_usage/A/prompts/test.md"]:
            item = self.entry()
            item["prompt_files"] = [reference]
            self.write("B", [item])
            with self.assertRaises((ValueError, OSError)):
                load_records(self.root)

    def test_bad_numbers_missing_model_and_naive_time_are_rejected(self):
        base = self.entry()
        bad = [{"calls": True}, {"calls": -1}, {"time": "2026-10-26T11:00:00"},
               {"cost": {"kind": "actual", "amount": float("nan"), "currency": "CNY", "basis": "test"}}]
        missing = deepcopy(base)
        del missing["model"]
        for item in [{**base, **change} for change in bad] + [missing]:
            self.write("B", [item])
            with self.assertRaises(ValueError):
                load_records(self.root)

    def test_likely_credential_in_prompt_is_rejected(self):
        (self.root / "ai_usage/B/prompts/test.md").write_text("sk-" + "x" * 24, encoding="utf-8")
        self.write("B", [self.entry()])
        with self.assertRaises(ValueError):
            load_records(self.root)


if __name__ == "__main__":
    unittest.main()
