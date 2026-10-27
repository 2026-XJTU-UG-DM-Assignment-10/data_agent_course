"""Member B offline acceptance tests. Run: python checks/check_B.py [--integration]."""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaner import clean_training_data, transform_test_data
from src.normalization import normalize_frame
from src.schema import (CleaningPlan, DataValidationError, FEATURE_COLUMNS,
                        NUMERIC_COLUMNS, NUMERIC_BOUNDS, TARGET_COLUMN)

def check():
    checks = []
    def verify(name, condition):
        assert condition, name
        checks.append(name)

    train = pd.read_csv(ROOT / "examples/train_small.csv", dtype=str, keep_default_na=False)
    test = pd.read_csv(ROOT / "examples/test_small.csv", dtype=str, keep_default_na=False)
    train_original, test_original = train.copy(deep=True), test.copy(deep=True)
    plan = CleaningPlan.model_validate_json((ROOT / "examples/plan_rules.json").read_text())
    norm, na = normalize_frame(train)
    norm2, na2 = normalize_frame(norm)
    assert_frame_equal(norm, norm2)
    verify("normalization_idempotent", na2.format_cells_changed == 0 and na2.parse_error_cells == 0)
    verify("normalization_audit", na.format_cells_changed >= 1 and na.parse_error_cells == 0)
    verify("outlier_retained_for_profiler", norm.iloc[3]["age"] == -5)
    clean, state, audit = clean_training_data(train, plan)
    assert_frame_equal(train, train_original)
    verify("train_input_untouched", True)
    verify("training_dedup", (audit.input_rows, audit.output_rows, audit.duplicate_rows_removed_before_fill) == (8, 7, 1))
    verify("invalid_mask_and_fill", audit.invalid_cells_set_missing == 2 and clean.loc[3, "age"] == 38.5 and clean.loc[3, "hours_per_week"] == 40)
    verify("reference_clean_values", list(clean[list(FEATURE_COLUMNS)].astype(str).columns) == list(FEATURE_COLUMNS) and not clean[list(FEATURE_COLUMNS)].isna().any().any())
    reference = pd.read_csv(ROOT / "examples/clean_train_small.csv")
    for col in FEATURE_COLUMNS:
        if col in NUMERIC_COLUMNS:
            verify("reference_"+col, clean[col].reset_index(drop=True).round(7).equals(reference[col].round(7)))
        else:
            verify("reference_"+col, clean[col].reset_index(drop=True).equals(reference[col]))
    expected_state = json.loads((ROOT / "examples/cleaning_state_example.json").read_text())
    verify("state_reference", state.model_dump(mode="json") == expected_state)
    snapshot = state.model_dump_json()
    test_clean, test_audit = transform_test_data(test, state)
    assert_frame_equal(test, test_original)
    verify("test_input_untouched", True)
    verify("test_no_refit", state.model_dump_json() == snapshot and test_audit.dataset == "test")
    verify("test_preserves_order_rows_labels_ids", len(test_clean) == len(test) and test_clean[TARGET_COLUMN].tolist() == test[TARGET_COLUMN].tolist() and test_clean["_source_id"].tolist() == test["_source_id"].tolist() and test_audit.duplicate_rows_removed_before_fill == test_audit.duplicate_rows_removed_after_fill == 0)
    verify("unseen_test_category", test_clean.loc[2, "workclass"] == "Unseen-example-workclass")
    # Independent synthetic scenario: two previously distinct rows collapse AFTER fill.
    synthetic = train.iloc[:4].copy().reset_index(drop=True)
    synthetic.loc[1, "age"] = "?"
    synthetic.loc[1, "workclass"] = synthetic.loc[0, "workclass"]
    for col in FEATURE_COLUMNS:
        if col != "age":
            synthetic.loc[1, col] = synthetic.loc[0, col]
    synthetic.loc[1, TARGET_COLUMN] = synthetic.loc[0, TARGET_COLUMN]
    synthetic.loc[2, "age"] = "39"
    synthetic.loc[3, "age"] = "39"
    # Keep rows 2,3 distinct from row 0 by workclass and fnlwgt.
    synthetic.loc[2, "workclass"] = "X"
    synthetic.loc[3, "workclass"] = "Y"
    second_plan = plan.model_copy(update={"categorical_imputation": "most_frequent"})
    second, second_state, second_audit = clean_training_data(synthetic, second_plan)
    verify("post_fill_dedup", second_audit.duplicate_rows_removed_after_fill == 1 and len(second) == 3)
    # Ties in mode use sorted lexical order.
    tie = synthetic.copy()
    tie["workclass"] = ["Zulu", "Alpha", "?", "?"]
    _, tie_state, _ = clean_training_data(tie, second_plan)
    verify("mode_tie_lexical", tie_state.categorical_fill_values["workclass"] == "Alpha")
    all_cat = synthetic.copy()
    all_cat["workclass"] = "?"
    _, cat_state, cat_audit = clean_training_data(all_cat, second_plan)
    verify("all_missing_category", cat_state.categorical_fill_values["workclass"] == "Unknown" and any("workclass" in w for w in cat_audit.warnings))
    all_num = synthetic.copy()
    all_num["age"] = "?"
    try:
        clean_training_data(all_num, plan)
    except DataValidationError:
        verify("all_missing_numeric_rejected", True)
    else:
        raise AssertionError("all missing numeric must fail")
    malformed = synthetic.copy()
    malformed.loc[0, "age"] = "forty"
    malformed.loc[1, "hours_per_week"] = "40 minutes"
    normalized, errors = normalize_frame(malformed)
    verify("unsupported_numeric_parse", errors.parse_error_cells == 2 and pd.isna(normalized.loc[0, "age"]) and pd.isna(normalized.loc[1, "hours_per_week"]))
    invalid_label = synthetic.copy()
    invalid_label.loc[0, TARGET_COLUMN] = "maybe"
    try:
        normalize_frame(invalid_label)
    except DataValidationError:
        verify("invalid_label_rejected", True)
    else:
        raise AssertionError("invalid label must fail")
    repeated_test = pd.concat([test.iloc[[0]], test.iloc[[0]]], ignore_index=True)
    repeated_clean, repeated_audit = transform_test_data(repeated_test, state)
    verify("test_duplicates_retained", len(repeated_clean) == 2 and repeated_audit.input_rows == repeated_audit.output_rows)
    return {"checks_passed": len(checks), "checks": checks,
            "train_audit": audit.model_dump(mode="json"),
            "test_audit": test_audit.model_dump(mode="json"),
            "uses_test_doubles": False, "shared_fixtures_are_not_experiments": True}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--integration", action="store_true")
    args = parser.parse_args()
    try:
        result = check()
        print(json.dumps({"status": "passed", "integration": args.integration, **result}, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"status":"failed", "error":str(exc)},ensure_ascii=False), file=sys.stderr)
        raise
