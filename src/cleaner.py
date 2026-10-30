"""Train-only fitting and leakage-free test transformation for Adult data."""

from __future__ import annotations

import math

import pandas as pd

from .normalization import normalize_frame
from .schema import (
    CATEGORY_FILL_VALUE, CATEGORICAL_COLUMNS, CleaningAudit, CleaningPlan,
    CleaningState, DataValidationError, FEATURE_COLUMNS, NUMERIC_BOUNDS,
    NUMERIC_COLUMNS, TARGET_COLUMN,
)

_DUPLICATE_KEY = list(FEATURE_COLUMNS) + [TARGET_COLUMN]


def _mask_invalid(frame: pd.DataFrame) -> int:
    """Set successfully parsed but out-of-bounds numeric cells to NaN."""
    total = 0
    for column in NUMERIC_COLUMNS:
        lower, upper = NUMERIC_BOUNDS[column]
        values = frame[column]
        invalid = values.notna() & (
            (values <= lower if column == "fnlwgt" else values < lower)
            | (values > upper if upper is not None else False)
        )
        total += int(invalid.sum())
        frame.loc[invalid, column] = float("nan")
    return total


def _fit_state(frame: pd.DataFrame, plan: CleaningPlan) -> tuple[CleaningState, list[str]]:
    numeric = {}
    for column in NUMERIC_COLUMNS:
        observed = frame[column].dropna()
        if observed.empty:
            raise DataValidationError(f"No valid training observations in numeric column: {column}")
        candidate = observed.mean() if plan.numeric_imputation == "mean" else observed.median()
        value = float(candidate)
        if not math.isfinite(value):
            raise DataValidationError(f"Non-finite imputation value in {column}")
        numeric[column] = value

    categorical = {}
    warnings = []
    for column in CATEGORICAL_COLUMNS:
        if plan.categorical_imputation == "constant":
            fill = plan.categorical_fill_value
        else:
            counts = frame[column].dropna().value_counts()
            if counts.empty:
                fill = CATEGORY_FILL_VALUE
            else:
                most = counts.max()
                fill = sorted(str(x) for x in counts.index[counts == most])[0]
        if frame[column].isna().all():
            warnings.append(f"Category column {column} is all missing; fill with Unknown")
            fill = CATEGORY_FILL_VALUE
        categorical[column] = fill
    return CleaningState(
        plan=plan, numeric_fill_values=numeric,
        categorical_fill_values=categorical,
        feature_columns=FEATURE_COLUMNS,
    ), warnings


def _validate_state(state: CleaningState) -> None:
    if not isinstance(state, CleaningState):
        raise DataValidationError("cleaning_state must be a CleaningState object")
    for column, value in state.numeric_fill_values.items():
        lower, upper = NUMERIC_BOUNDS[column]
        if not math.isfinite(value) or (value <= lower if column == "fnlwgt" else value < lower) or (upper is not None and value > upper):
            raise DataValidationError(f"Invalid training fill value for {column}: {value}")
    for column, value in state.categorical_fill_values.items():
        if not isinstance(value, str) or not value or value.strip() != value:
            raise DataValidationError(f"Invalid category fill for {column}")


def _fill(frame: pd.DataFrame, state: CleaningState) -> int:
    """Return number of missing feature cells filled before the final dedup."""
    filled = 0
    for column in NUMERIC_COLUMNS:
        missing = frame[column].isna()
        filled += int(missing.sum())
        frame[column] = frame[column].fillna(state.numeric_fill_values[column]).astype("float64")
    for column in CATEGORICAL_COLUMNS:
        missing = frame[column].isna()
        filled += int(missing.sum())
        frame[column] = frame[column].fillna(state.categorical_fill_values[column])
    return filled


def clean_training_data(
    train_df: pd.DataFrame, plan: CleaningPlan,
) -> tuple[pd.DataFrame, CleaningState, CleaningAudit]:
    """Normalize → dedup → mask invalid → train-fit → fill → dedup.

    Duplicate comparisons use exactly 14 normalized features and the label,
    never metadata IDs. Rows are only removed for duplicates, never for nulls.
    """
    if not isinstance(plan, CleaningPlan):
        raise DataValidationError("plan must be a validated CleaningPlan object")
    frame, normalization = normalize_frame(train_df)
    input_rows = len(frame)
    before = int(frame.duplicated(subset=_DUPLICATE_KEY, keep="first").sum())
    frame = frame.drop_duplicates(subset=_DUPLICATE_KEY, keep="first").copy()
    invalid = _mask_invalid(frame)
    state, warnings = _fit_state(frame, plan)
    missing_filled = _fill(frame, state)
    after = int(frame.duplicated(subset=_DUPLICATE_KEY, keep="first").sum())
    frame = frame.drop_duplicates(subset=_DUPLICATE_KEY, keep="first").copy()
    audit = CleaningAudit(
        dataset="train", input_rows=input_rows, output_rows=len(frame),
        format_cells_changed=normalization.format_cells_changed,
        parse_error_cells=normalization.parse_error_cells,
        invalid_cells_set_missing=invalid,
        missing_cells_filled=missing_filled,
        duplicate_rows_removed_before_fill=before,
        duplicate_rows_removed_after_fill=after, warnings=warnings,
    )
    return frame, state, audit


def transform_test_data(
    test_df: pd.DataFrame, cleaning_state: CleaningState,
) -> tuple[pd.DataFrame, CleaningAudit]:
    """Apply *only* trained fill values; do not fit, drop, reorder, or mutate."""
    _validate_state(cleaning_state)
    frame, normalization = normalize_frame(test_df)
    input_rows = len(frame)
    invalid = _mask_invalid(frame)
    missing_filled = _fill(frame, cleaning_state)
    audit = CleaningAudit(
        dataset="test", input_rows=input_rows, output_rows=len(frame),
        format_cells_changed=normalization.format_cells_changed,
        parse_error_cells=normalization.parse_error_cells,
        invalid_cells_set_missing=invalid,
        missing_cells_filled=missing_filled,
        duplicate_rows_removed_before_fill=0,
        duplicate_rows_removed_after_fill=0,
    )
    return frame, audit
