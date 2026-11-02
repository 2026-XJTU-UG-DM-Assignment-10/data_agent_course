"""Reproduce B's formal-data cases and all allowed strategies, without an API.

Run from project root: python evidence/B/verify_stage2.py
Manifests are used for provenance checks only, never as cleaner inputs.
"""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.agent import get_cleaning_plan
from src.cleaner import clean_training_data, transform_test_data
from src.normalization import normalize_frame
from src.profiler import profile_data
from src.schema import (CATEGORICAL_COLUMNS, CleaningPlan, FEATURE_COLUMNS,
                        METADATA_COLUMNS, NUMERIC_BOUNDS, NUMERIC_COLUMNS,
                        TARGET_COLUMN)

OUT = ROOT / "outputs/member_B/codex_20261102"
KEY = list(FEATURE_COLUMNS) + [TARGET_COLUMN]
PROTECTED = [TARGET_COLUMN, *METADATA_COLUMNS]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read(name):
    return pd.read_csv(ROOT / name, dtype=str, keep_default_na=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data_paths = ["data/dirty/train_dirty.csv", "data/reference/test_reference.csv"]
    hashes = {p: digest(ROOT / p) for p in data_paths}
    manifest = json.loads((ROOT / "data/manifests/preparation_summary.json").read_text(encoding="utf-8"))
    for p, value in hashes.items():
        assert value == manifest["outputs"][p]["sha256"]
    train, test = (read(p) for p in data_paths)
    originals = train.copy(deep=True), test.copy(deep=True)
    assert not set(train["_group_id"]) & set(test["_group_id"])
    before = profile_data(train)
    plan = get_cleaning_plan(before, mode="rules")
    clean, state, audit = clean_training_data(train, plan)
    snapshot = state.model_dump_json()
    test_clean, test_audit = transform_test_data(test, state)
    assert state.model_dump_json() == snapshot
    assert_frame_equal(train, originals[0])
    assert_frame_equal(test, originals[1])
    assert_frame_equal(test_clean[PROTECTED], test[PROTECTED])
    assert test_clean.index.equals(test.index)
    assert_frame_equal(clean[PROTECTED], train.loc[clean.index, PROTECTED])
    assert not clean[list(FEATURE_COLUMNS)].isna().any().any()
    assert not test_clean[list(FEATURE_COLUMNS)].isna().any().any()
    assert audit.input_rows - audit.output_rows == audit.duplicate_rows_removed_before_fill + audit.duplicate_rows_removed_after_fill
    normalized, normalization_audit = normalize_frame(train)
    initial_dup = normalized.duplicated(subset=KEY, keep="first")
    fit_input = normalized.loc[~initial_dup].copy(deep=True)
    for col in NUMERIC_COLUMNS:
        low, high = NUMERIC_BOUNDS[col]
        invalid = (fit_input[col] <= low if col == "fnlwgt" else fit_input[col] < low)
        if high is not None:
            invalid |= fit_input[col] > high
        fit_input.loc[invalid, col] = float("nan")
    removed_missing = int(normalized.loc[initial_dup, list(FEATURE_COLUMNS)].isna().sum().sum())
    assert sum(before.missing_by_column.values()) - removed_missing + audit.invalid_cells_set_missing == audit.missing_cells_filled

    cases = []
    for problem, source, column in [("missing", "S016453", "native_country"),
                                    ("outlier", "S002083", "age"),
                                    ("format", "S010642", "fnlwgt")]:
        indices = train.index[train["_source_id"] == source].tolist()
        assert len(indices) == 1
        index = indices[0]
        assert index in clean.index
        value = normalized.at[index, column]
        cases.append({"problem_type": problem, "source_id": source,
                      "group_id": train.at[index, "_group_id"], "field": column,
                      "dirty_position_zero_based": index, "raw_value": train.at[index, column],
                      "normalized_value": None if pd.isna(value) else float(value) if column in NUMERIC_COLUMNS else value,
                      "output_value": float(clean.at[index, column]) if column in NUMERIC_COLUMNS else clean.at[index, column],
                      "output_csv_position_zero_based": clean.index.get_loc(index).item() if hasattr(clean.index.get_loc(index), "item") else clean.index.get_loc(index)})
    missing, outlier, formatting = cases
    assert pd.isna(normalized.at[missing["dirty_position_zero_based"], "native_country"])
    assert missing["output_value"] == state.categorical_fill_values["native_country"] == "Unknown"
    assert outlier["normalized_value"] < NUMERIC_BOUNDS["age"][0]
    assert outlier["output_value"] == state.numeric_fill_values["age"]
    assert formatting["raw_value"].strip() != formatting["raw_value"]
    assert float(formatting["raw_value"]) == formatting["output_value"]
    positions = train.index[train["_source_id"] == "S025957"].tolist()
    assert len(positions) == 2
    assert_series_equal(normalized.loc[positions[0], KEY], normalized.loc[positions[1], KEY], check_names=False)
    retained = [i for i in positions if i in clean.index]
    removed = [i for i in positions if i not in clean.index]
    assert retained == [positions[0]] and removed == [positions[1]] and initial_dup.at[removed[0]]
    cases.insert(1, {"problem_type": "duplicate", "source_id": "S025957", "field": "14 features + income",
                     "group_ids": train.loc[positions, "_group_id"].tolist(), "dirty_positions_zero_based": positions,
                     "retained_original_positions": retained, "removed_original_positions": removed,
                     "metadata_excluded_from_key": True, "normalized_full_key_equal": True,
                     "output_value": "one retained, one removed in first dedup"})
    after = profile_data(clean, stage="after")
    assert sum(after.missing_by_column.values()) == after.duplicate_rows == after.outlier_cells == after.format_issue_cells == 0
    matrix = []
    for numeric in ("mean", "median"):
        for categorical in ("most_frequent", "constant"):
            selected = CleaningPlan(mode="rules", numeric_imputation=numeric,
                                    categorical_imputation=categorical,
                                    reason_numeric="B offline strategy allowlist verification; no model request",
                                    reason_categorical="B offline strategy allowlist verification; no model request")
            transformed, fitted, train_audit = clean_training_data(train, selected)
            fitted_snapshot = fitted.model_dump_json()
            transformed_test, ta = transform_test_data(test, fitted)
            assert fitted.model_dump_json() == fitted_snapshot
            assert_frame_equal(train, originals[0])
            assert_frame_equal(test, originals[1])
            assert_frame_equal(transformed_test[PROTECTED], test[PROTECTED])
            assert_frame_equal(transformed[PROTECTED], train.loc[transformed.index, PROTECTED])
            assert not transformed[list(FEATURE_COLUMNS)].isna().any().any()
            assert not transformed_test[list(FEATURE_COLUMNS)].isna().any().any()
            for col in NUMERIC_COLUMNS:
                observations = fit_input[col].dropna()
                expected = observations.mean() if numeric == "mean" else observations.median()
                assert fitted.numeric_fill_values[col] == float(expected)
            for col in CATEGORICAL_COLUMNS:
                counts = fit_input[col].dropna().value_counts()
                expected = "Unknown" if categorical == "constant" or counts.empty else sorted(counts.index[counts == counts.max()])[0]
                assert fitted.categorical_fill_values[col] == expected
            matrix.append({"numeric_strategy": numeric, "categorical_strategy": categorical,
                           "train_audit": train_audit.model_dump(mode="json"), "test_audit": ta.model_dump(mode="json"),
                           "state": fitted.model_dump(mode="json")})
    clean.to_csv(OUT / "train_clean_rules.csv", index=False, encoding="utf-8")
    test_clean.to_csv(OUT / "test_transformed_rules.csv", index=False, encoding="utf-8")
    result = {"status": "passed", "checked_at": datetime.now(timezone.utc).isoformat(),
              "mode": "rules/direct_B_modules", "pipeline_run_id": None, "real_model_requests": 0,
              "uses_test_doubles": False, "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "python": platform.python_version(), "dependencies": {p: importlib.metadata.version(p) for p in ("pandas", "numpy", "pydantic", "scikit-learn", "requests", "streamlit", "matplotlib")},
              "source_data_sha256": hashes, "plan": plan.model_dump(mode="json"), "state": state.model_dump(mode="json"),
              "train_audit": audit.model_dump(mode="json"), "test_audit": test_audit.model_dump(mode="json"),
              "normalization_audit": normalization_audit.model_dump(mode="json"),
              "before": before.model_dump(mode="json"), "after": after.model_dump(mode="json"),
              "missing_in_first_dedup_removed_rows": removed_missing, "cases": cases, "strategy_matrix": matrix,
              "assertions": {"inputs_unchanged": True, "test_rows_index_labels_ids_unchanged": True,
                             "train_survivor_labels_ids_unchanged": True, "state_unchanged": True,
                             "training_only_fill_values_independently_checked": True, "train_test_groups_disjoint": True},
              "output_sha256": {p: digest(OUT / p) for p in ("train_clean_rules.csv", "test_transformed_rules.csv")}}
    write("formal_verification.json", result)
    print(json.dumps({"status": "passed", "train_audit": result["train_audit"], "test_audit": result["test_audit"],
                      "cases": cases, "strategies": [{"numeric": m["numeric_strategy"], "categorical": m["categorical_strategy"], "rows": m["train_audit"]["output_rows"]} for m in matrix]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
