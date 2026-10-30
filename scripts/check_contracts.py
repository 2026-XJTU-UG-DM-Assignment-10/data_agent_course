"""Validate shared contracts and tiny fixtures; no business or API execution."""

from __future__ import annotations

import ast
import csv
import json
import sys
from pathlib import Path

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src import contracts  # noqa: E402,F401
from src.schema import (  # noqa: E402
    CATEGORICAL_COLUMNS, CSV_COLUMNS, FEATURE_COLUMNS, MISSING_TOKENS,
    NUMERIC_COLUMNS, CleaningAudit, CleaningPlan, RunResult,
)


def expect_rejected(name: str, model: type, payload: dict) -> str:
    try:
        model.model_validate(payload)
    except ValidationError:
        return name
    raise AssertionError(f"Invalid case was accepted: {name}")


def main() -> None:
    for filename in ("__init__.py", "schema.py", "contracts.py"):
        path = PROJECT_ROOT / "src" / filename
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    examples = PROJECT_ROOT / "examples"
    plan = CleaningPlan.model_validate_json(
        (examples / "plan_rules.json").read_text(encoding="utf-8")
    )
    assert plan.mode == "rules"
    assert CleaningPlan.model_validate_json(plan.model_dump_json()) == plan

    payload = plan.model_dump(mode="json")
    rejected = [
        expect_rejected(
            "unsupported_strategy", CleaningPlan,
            json.loads((examples / "plan_invalid.json").read_text(encoding="utf-8")),
        ),
        expect_rejected("unexpected_field", CleaningPlan, {**payload, "python_code": "print(1)"}),
        expect_rejected("wrong_step_order", CleaningPlan, {**payload, "steps": list(reversed(plan.steps))}),
        expect_rejected(
            "deleting_test_row", CleaningAudit,
            {"dataset": "test", "input_rows": 3, "output_rows": 2,
             "duplicate_rows_removed_before_fill": 1},
        ),
        expect_rejected(
            "success_without_metrics", RunResult,
            {"run_id": "contract-check", "status": "succeeded",
             "mode": "rules", "output_dir": "example"},
        ),
    ]

    rows = {}
    for name in ("train_small", "test_small"):
        with (examples / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            assert tuple(reader.fieldnames or ()) == CSV_COLUMNS
            rows[name] = list(reader)
            assert all(set(row) == set(CSV_COLUMNS) for row in rows[name])

    train, test = rows["train_small"], rows["test_small"]
    assert len(train) == 8 and len(test) == 3
    assert not ({row["_group_id"] for row in train} & {row["_group_id"] for row in test})
    missing = sum(
        row[column].strip().casefold() in MISSING_TOKENS
        for row in train for column in FEATURE_COLUMNS
    )
    assert missing == 2
    signatures = [tuple(row[column] for column in (*FEATURE_COLUMNS, "income")) for row in train]
    assert len(signatures) - len(set(signatures)) == 1
    assert len(NUMERIC_COLUMNS) == 6 and len(CATEGORICAL_COLUMNS) == 8

    print(json.dumps({
        "status": "passed",
        "scope": "shared contracts and fixtures only; business acceptance is checked separately",
        "rejected_invalid_cases": rejected,
        "fixture_rows": {name: len(value) for name, value in rows.items()},
        "fixture_columns": len(CSV_COLUMNS),
        "fixture_missing_cells": missing,
        "source_groups_disjoint": True,
    }, indent=2))


if __name__ == "__main__":
    main()
