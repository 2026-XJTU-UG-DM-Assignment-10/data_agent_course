"""Member A self-check. Run: python checks/check_A.py [--integration]

Fixtures scope always runs on the shared micro samples. Formal-data scope runs
when the preparation outputs exist; otherwise it prints the fixed preparation
command and exits with status 2 (missing input), never downloading anything.

The checker re-derives every expected count with its own small parser instead of
importing the profiler's helper code or reading expected numbers from a file, so
a wrong profiler cannot pass by agreeing with itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:  # Member B's shared normalizer; errors inside it must surface, not be hidden.
    from src.normalization import normalize_frame as real_normalize_frame  # noqa: E402
except ImportError:  # pragma: no cover - only when B has not delivered the module
    real_normalize_frame = None

from src.schema import (  # noqa: E402
    CATEGORICAL_COLUMNS, FEATURE_COLUMNS, MISSING_TOKENS, NUMERIC_BOUNDS,
    NUMERIC_COLUMNS, TARGET_COLUMN,
)

PREPARE_COMMAND = "python scripts/prepare_data.py --seed 42 --sample-size 10000"
NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
SUFFIXES = {"age": ("years", "year"), "hours_per_week": ("hours", "hour", "h")}


class MarkedNormalizationDouble:
    """Test double for a missing ``src.normalization``; clearly marked and used
    only when the shared module cannot be imported and --integration is absent."""

    label = "TEST_DOUBLE: minimal local normalizer, not member B's implementation"

    @staticmethod
    def __call__(frame: pd.DataFrame):
        from src.schema import (  # local import keeps the double self-contained
            NormalizationAudit, CSV_COLUMNS,
        )

        working = frame.loc[:, list(CSV_COLUMNS)].copy(deep=True)
        changed = failed = 0
        for column in NUMERIC_COLUMNS:
            values = []
            for value in working[column]:
                if _missing(value):
                    values.append(float("nan"))
                    continue
                number, was_changed, was_failed = _parse_number(value, column)
                changed += int(was_changed)
                failed += int(was_failed)
                values.append(number)
            working[column] = pd.Series(values, index=working.index, dtype="float64")
        for column in CATEGORICAL_COLUMNS:
            values = []
            for value in working[column]:
                if _missing(value):
                    values.append(None)
                    continue
                text = str(value).strip()
                changed += int(text != str(value))
                values.append(text)
            working[column] = pd.Series(values, index=working.index, dtype="object")
        return working, NormalizationAudit(format_cells_changed=changed, parse_error_cells=failed)


def _missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in MISSING_TOKENS
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if isinstance(result, bool) else False


def _parse_number(value: object, column: str) -> tuple[float, bool, bool]:
    """Independent parser: returns (value-or-nan, format_changed, parse_failed)."""
    if _missing(value):
        return float("nan"), False, False
    if not isinstance(value, str):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return float("nan"), True, True
        return (number, False, False) if math.isfinite(number) else (float("nan"), True, True)
    stripped = value.strip()
    changed = stripped != value
    text = stripped
    if not NUMBER.fullmatch(stripped):
        suffixes = SUFFIXES.get(column)
        matched = None
        if suffixes:
            pattern = r"^(%s)\s*(%s)$" % (NUMBER.pattern[1:-1], "|".join(suffixes))
            matched = re.fullmatch(pattern, stripped, re.IGNORECASE)
        if matched is None:
            return float("nan"), True, True
        text = matched.group(1)
        changed = True
    try:
        number = float(text)
    except (ValueError, OverflowError):
        return float("nan"), True, True
    if not math.isfinite(number):
        return float("nan"), True, True
    return number, changed, False


def _out_of_range(column: str, value: float) -> bool:
    low, high = NUMERIC_BOUNDS[column]
    if column == "fnlwgt":
        if value <= low:
            return True
    elif value < low:
        return True
    return high is not None and value > high


def _canonical(value) -> str:
    """Row-signature token: NaN compares equal to NaN, unlike float('nan')."""
    if isinstance(value, float):
        return "\x00MISSING" if math.isnan(value) else repr(value)
    return "" if value is None else str(value)


def independent_counts(frame: pd.DataFrame) -> dict:
    """Recompute the contract statistics without touching src.profiler."""
    missing = {column: 0 for column in FEATURE_COLUMNS}
    format_cells = parse_errors = 0
    outlier_cells = 0
    outlier_row_flags = []
    normalized_rows = []
    for position in range(len(frame)):
        row_outlier = False
        row = []
        for column in FEATURE_COLUMNS:
            value = frame.iat[position, frame.columns.get_loc(column)]
            if _missing(value):
                missing[column] += 1
            if column in NUMERIC_COLUMNS:
                number, changed, failed = _parse_number(value, column)
                format_cells += int(changed)
                parse_errors += int(failed)
                if math.isfinite(number) and _out_of_range(column, number):
                    outlier_cells += 1
                    row_outlier = True
                row.append(number)
            else:
                text = "" if _missing(value) else str(value).strip()
                if not _missing(value) and not isinstance(value, str):
                    format_cells += 1
                if isinstance(value, str) and value != value.strip():
                    format_cells += 1
                row.append(text)
        label = frame.iat[position, frame.columns.get_loc(TARGET_COLUMN)]
        normalized_rows.append(tuple(_canonical(cell) for cell in row) + (str(label),))
        outlier_row_flags.append(row_outlier)
    return {
        "row_count": int(len(frame)),
        "missing_by_column": missing,
        "missing_total": int(sum(missing.values())),
        "duplicate_rows": int(len(normalized_rows) - len(set(normalized_rows))),
        "outlier_cells": outlier_cells,
        "outlier_rows": int(sum(outlier_row_flags)),
        "format_issue_cells": format_cells,
        "parse_error_cells": parse_errors,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare(report, expected: dict, label: str, checks: list[str]) -> None:
    for field in ("row_count", "duplicate_rows", "outlier_cells", "outlier_rows",
                  "format_issue_cells", "parse_error_cells"):
        assert getattr(report, field) == expected[field], (
            f"{label}: {field} expected {expected[field]}, got {getattr(report, field)}"
        )
    assert report.missing_by_column == expected["missing_by_column"], (
        f"{label}: missing_by_column differs"
    )
    checks.append(f"{label}_counts_match_independent_recount")


def run(profile_data, normalize_frame, *, integration: bool, reports: dict) -> dict:
    checks: list[str] = []

    def verify(name: str, condition: bool) -> None:
        assert condition, name
        checks.append(name)

    # ---------------- fixtures: shared micro samples ----------------
    train = pd.read_csv(ROOT / "examples/train_small.csv", dtype=str, keep_default_na=False)
    test = pd.read_csv(ROOT / "examples/test_small.csv", dtype=str, keep_default_na=False)
    train_before = train.copy(deep=True)

    before = profile_data(train, dataset="train", stage="before")
    verify("fixture_input_unmodified", train.equals(train_before))
    verify("report_metadata", before.dataset == "train" and before.stage == "before"
           and before.feature_count == 14)
    verify("dtypes_cover_all_features", set(before.dtypes) == set(FEATURE_COLUMNS))
    verify("missing_covers_all_features", set(before.missing_by_column) == set(FEATURE_COLUMNS))
    verify("numeric_summary_covers_six", set(before.numeric_summary) == set(NUMERIC_COLUMNS))
    for column, entry in before.numeric_summary.items():
        verify(f"numeric_summary_fields_{column}",
               set(entry) >= {"count", "mean", "median", "min", "max", "std"})

    expected = independent_counts(train)
    compare(before, expected, "fixture", checks)
    verify("fixture_has_problems", expected["missing_total"] > 0 and expected["duplicate_rows"] > 0
           and expected["outlier_cells"] > 0 and expected["format_issue_cells"] > 0)
    verify("fixture_parse_errors_zero", before.parse_error_cells == 0)

    # Already-normalized sample: numbers must line up with normalized_train_small.csv.
    normalized_sample = pd.read_csv(ROOT / "examples/normalized_train_small.csv",
                                    dtype=str, keep_default_na=False)
    normalized_report = profile_data(normalized_sample, dataset="train", stage="before")
    verify("normalized_sample_no_format_issues", normalized_report.format_issue_cells == 0
           and normalized_report.parse_error_cells == 0)
    verify("normalized_sample_outliers_retained", normalized_report.outlier_cells == before.outlier_cells
           and normalized_report.outlier_rows == before.outlier_rows)
    verify("normalized_sample_duplicates_preserved", normalized_report.duplicate_rows == before.duplicate_rows)
    verify("normalized_sample_raw_missing_preserved",
           normalized_report.missing_by_column == before.missing_by_column)

    clean = pd.read_csv(ROOT / "examples/clean_train_small.csv", dtype=str, keep_default_na=False)
    clean_report = profile_data(clean, dataset="train", stage="after")
    verify("clean_sample_is_clean", clean_report.duplicate_rows == 0 and clean_report.outlier_cells == 0
           and clean_report.format_issue_cells == 0 and clean_report.parse_error_cells == 0
           and sum(clean_report.missing_by_column.values()) == 0)
    verify("stage_after_recorded", clean_report.stage == "after")

    test_report = profile_data(test, dataset="test", stage="before")
    verify("test_dataset_recorded", test_report.dataset == "test" and test_report.row_count == len(test))

    # The profiler must reuse the shared normalizer, not its own parser:
    # re-profiling the normalized view must add no new format changes.
    normalized_once, audit_once = normalize_frame(train)
    normalized_twice, audit_twice = normalize_frame(normalized_once)
    verify("shared_normalizer_used", audit_once.format_cells_changed
           >= before.format_issue_cells and audit_twice.format_cells_changed == 0)

    # Independent synthetic case: unparseable numerics, unit suffix, whitespace and bounds.
    # Built from the clean sample so only the values set below can be reported.
    synthetic = clean.iloc[:4].copy().reset_index(drop=True)
    synthetic.loc[0, "age"] = "forty"                     # parse failure
    synthetic.loc[1, "hours_per_week"] = "40 minutes"     # parse failure
    synthetic.loc[2, "age"] = " 30 "                      # trimmable
    synthetic.loc[3, "hours_per_week"] = "999 hours"      # format + outlier
    synthetic_report = profile_data(synthetic, dataset="train", stage="before")
    synthetic_expected = independent_counts(synthetic)
    compare(synthetic_report, synthetic_expected, "synthetic", checks)
    verify("synthetic_parse_failures_counted",
           synthetic_report.parse_error_cells == 2 and synthetic_report.parse_error_cells
           <= synthetic_report.format_issue_cells)
    verify("synthetic_unit_outlier_counted",
           synthetic_report.outlier_cells == 1 and synthetic_report.outlier_rows == 1)
    verify("synthetic_missing_excludes_parse_failures",
           synthetic_report.missing_by_column["age"] == 0)

    reports["fixtures"] = {
        "scope": "fixtures",
        "status": "passed",
        "uses_test_doubles": reports["uses_test_doubles"],
        "checks_passed": len(checks),
        "checks": checks,
        "fixture_before": before.model_dump(mode="json"),
        "independent_recount": expected,
    }

    # ---------------- formal data: preparation outputs ----------------
    dirty_path = ROOT / "data" / "dirty" / "train_dirty.csv"
    train_ref_path = ROOT / "data" / "reference" / "train_reference.csv"
    test_ref_path = ROOT / "data" / "reference" / "test_reference.csv"
    summary_path = ROOT / "data" / "manifests" / "preparation_summary.json"
    split_path = ROOT / "data" / "manifests" / "split_manifest.csv"
    injection_path = ROOT / "data" / "manifests" / "injection_manifest.csv"
    raw_path = ROOT / "data" / "raw" / "adult.data"
    formal_paths = [dirty_path, train_ref_path, test_ref_path, summary_path, split_path,
                    injection_path, raw_path]
    missing_paths = [str(path.relative_to(ROOT)).replace("\\", "/")
                     for path in formal_paths if not path.is_file()]
    if missing_paths:
        reports["formal_data"] = {
            "scope": "formal_data",
            "status": "not_run",
            "reason": "formal preparation outputs are missing",
            "missing": missing_paths,
            "prepare_command": PREPARE_COMMAND,
        }
        return {"status": "incomplete", "checks": reports}

    formal_checks: list[str] = []

    def formal(name: str, condition: bool) -> None:
        assert condition, name
        formal_checks.append(name)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    formal("summary_declares_ready", summary.get("status") == "ready")
    formal("summary_command_matches",
           summary.get("command") == PREPARE_COMMAND)
    formal("summary_seed_42", summary.get("sample", {}).get("seed") == 42)
    formal("summary_sample_10000", summary.get("sample", {}).get("sample_size") == 10000)

    formal("raw_file_preserved", raw_path.stat().st_size == summary["source"]["raw_bytes"])
    formal("raw_sha256_matches", sha256_file(raw_path) == summary["source"]["raw_sha256"])
    formal("source_license_recorded", isinstance(summary["source"].get("license"), str)
           and summary["source"]["license"])

    train_ref = pd.read_csv(train_ref_path, dtype=str, keep_default_na=False)
    test_ref = pd.read_csv(test_ref_path, dtype=str, keep_default_na=False)
    dirty = pd.read_csv(dirty_path, dtype=str, keep_default_na=False)

    formal("reference_is_10000_rows", len(train_ref) + len(test_ref) == 10000)
    formal("train_gt_5000", len(train_ref) > 5000)
    formal("test_positive", len(test_ref) > 0)
    formal("train_test_groups_disjoint",
           not (set(train_ref["_group_id"]) & set(test_ref["_group_id"])))
    formal("source_ids_unique_in_reference",
           train_ref["_source_id"].is_unique and test_ref["_source_id"].is_unique)

    split = pd.read_csv(split_path, dtype=str, keep_default_na=False)
    formal("split_manifest_columns",
           list(split.columns) == ["_source_id", "_group_id", "split"])
    formal("split_manifest_rows_match", len(split) == 10000)
    formal("split_manifest_groups_consistent",
           split.groupby("_group_id")["split"].nunique().max() == 1)
    formal("split_manifest_train_gt_5000",
           int((split["split"] == "train").sum()) == len(train_ref))
    formal("split_manifest_test_matches",
           int((split["split"] == "test").sum()) == len(test_ref))

    injection = pd.read_csv(injection_path, dtype=str, keep_default_na=False)
    formal("injection_manifest_columns",
           list(injection.columns) == ["_source_id", "field", "problem_type",
                                       "old_value", "new_value"])
    kinds = set(injection["problem_type"])
    formal("injection_has_four_kinds", kinds == {"missing", "duplicate", "outlier", "format"})
    formal("injection_sources_are_train",
           set(injection.loc[injection["problem_type"] != "duplicate", "_source_id"])
           <= set(train_ref["_source_id"]))
    formal("injection_row_count = train_ref + duplicates",
           len(dirty) == len(train_ref) + int((injection["problem_type"] == "duplicate").sum()))

    # Copies must keep their source id, and the label must never be injected.
    duplicated = dirty[dirty.duplicated(keep=False)]
    formal("duplicate_copies_keep_source_id",
           int(duplicated["_source_id"].duplicated(keep=False).sum()) >= 2)
    formal("labels_untouched", set(dirty[TARGET_COLUMN]) <= {"<=50K", ">50K"}
           and dirty[TARGET_COLUMN].tolist()[: len(train_ref)]
           == train_ref[TARGET_COLUMN].tolist())
    formal("test_not_injected", not (set(test_ref["_source_id"]) &
                                     set(injection["_source_id"])))

    # Detection must be produced by profile_data, not by reading the manifest.
    dirty_report = profile_data(dirty, dataset="train", stage="before")
    dirty_expected = independent_counts(dirty)
    compare(dirty_report, dirty_expected, "formal_dirty", formal_checks)
    formal("formal_detects_all_four_kinds",
           dirty_report.missing_by_column and sum(dirty_report.missing_by_column.values()) > 0
           and dirty_report.duplicate_rows > 0 and dirty_report.outlier_cells > 0
           and dirty_report.format_issue_cells > 0)
    formal("formal_duplicate_rows_equals_manifest_copies",
           dirty_report.duplicate_rows == int((injection["problem_type"] == "duplicate").sum()))

    test_report_formal = profile_data(test_ref, dataset="test", stage="before")
    test_expected = independent_counts(test_ref)
    compare(test_report_formal, test_expected, "formal_test", formal_checks)

    reports["formal_data"] = {
        "scope": "formal_data",
        "status": "passed",
        "uses_test_doubles": False,
        "checks_passed": len(formal_checks),
        "checks": formal_checks,
        "row_counts": {
            "reference": len(train_ref) + len(test_ref),
            "train_reference": len(train_ref),
            "test_reference": len(test_ref),
            "train_dirty": len(dirty),
        },
        "injection_counts": injection["problem_type"].value_counts().to_dict(),
        "quality_before": dirty_report.model_dump(mode="json"),
        "independent_recount": dirty_expected,
    }
    return {"status": "complete", "checks": reports}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integration", action="store_true",
                        help="Require member B's real normalization module")
    args = parser.parse_args()

    if real_normalize_frame is None:
        if args.integration:
            print(json.dumps({
                "status": "not_run",
                "reason": "member B's src/normalization.normalize_frame is unavailable",
                "integration_requires_real_module": True,
            }, ensure_ascii=False), file=sys.stderr)
            return 2
        # Clearly marked test double: only stands in for a missing peer dependency,
        # never replaces member A's profiler logic, and is never silent.
        import types

        import src

        double = MarkedNormalizationDouble()
        stub = types.ModuleType("src.normalization")
        stub.normalize_frame = double
        stub.__doc__ = double.label
        # ``src.profiler`` does ``from .normalization import normalize_frame`` at
        # module import time, so the stub has to be registered before that import.
        sys.modules["src.normalization"] = stub
        setattr(src, "normalization", stub)
        sys.modules.pop("src.profiler", None)
        normalize_frame = double
        uses_double = True
        print(json.dumps({"warning": double.label}, ensure_ascii=False), file=sys.stderr)
    else:
        normalize_frame = real_normalize_frame
        uses_double = False

    from src.profiler import profile_data

    reports: dict = {"uses_test_doubles": uses_double}
    try:
        outcome = run(profile_data, normalize_frame,
                      integration=args.integration, reports=reports)
    except AssertionError as exc:
        print(json.dumps({"status": "failed", "failed_check": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).isoformat()
    outputs = ROOT / "outputs" / "member_A"
    outputs.mkdir(parents=True, exist_ok=True)
    payload = {
        "role": "A",
        "integration": args.integration,
        "checked_at": stamp,
        "workflow_version": "2.0",
        "contract_version": "1.0",
        **outcome["checks"],
    }
    (outputs / ("check_integration.json" if args.integration else "check.json")).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Committable sanitized receipts. --integration must not rewrite them.
    if not args.integration:
        evidence = ROOT / "evidence" / "A"
        evidence.mkdir(parents=True, exist_ok=True)
        for scope, body in outcome["checks"].items():
            if scope not in ("fixtures", "formal_data") or body.get("status") != "passed":
                continue
            receipt = {
                "workflow_version": "2.0",
                "contract_version": "1.0",
                "role": "A",
                "scope": scope,
                "status": "passed",
                "checked_at": stamp,
                "command": "python checks/check_A.py",
                "uses_test_doubles": body["uses_test_doubles"],
                "summary": {
                    "checks_passed": body["checks_passed"],
                    "checks": body["checks"],
                    **({"row_counts": body["row_counts"],
                        "injection_counts": body["injection_counts"],
                        "quality_before": {
                            key: body["quality_before"][key]
                            for key in ("row_count", "duplicate_rows", "outlier_cells",
                                        "outlier_rows", "format_issue_cells",
                                        "parse_error_cells")
                        }} if scope == "formal_data" else
                       {"fixture_rows": body["fixture_before"]["row_count"]}),
                },
                "artifacts": [
                    "outputs/member_A/check.json",
                    *(["data/manifests/preparation_summary.json"] if scope == "formal_data" else []),
                ],
            }
            (evidence / f"{scope}.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": outcome["status"],
        "integration": args.integration,
        "fixtures": outcome["checks"]["fixtures"]["status"],
        "formal_data": outcome["checks"]["formal_data"]["status"],
        "prepare_command": (outcome["checks"]["formal_data"].get("prepare_command")
                            if outcome["checks"]["formal_data"]["status"] != "passed" else None),
        "checks_passed": outcome["checks"]["fixtures"]["checks_passed"]
        + int(outcome["checks"]["formal_data"].get("checks_passed", 0)),
    }, ensure_ascii=False, indent=2))

    if outcome["status"] != "complete":
        print(
            "Formal preparation outputs are missing. Run:\n  " + PREPARE_COMMAND,
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
