"""Quality profiling for the fixed Adult table (contract 1.0).

``profile_data`` never mutates its input and never consults the injection
manifest. All format handling comes from ``src.normalization.normalize_frame`` so
the profiler and the cleaner share one parser.
"""

from __future__ import annotations

import math

import pandas as pd

from .normalization import normalize_frame
from .schema import (
    FEATURE_COLUMNS, MISSING_TOKENS, NUMERIC_BOUNDS, NUMERIC_COLUMNS,
    TARGET_COLUMN, DatasetKind, QualityReport, ReportStage,
)

_SUMMARY_FIELDS = ("count", "mean", "median", "min", "max", "std")


def _is_raw_missing(value: object) -> bool:
    """Actual nulls plus the public missing tokens; parse failures stay out."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in MISSING_TOKENS
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if isinstance(result, bool) else False


def _is_out_of_range(column: str, value: float) -> bool:
    low, high = NUMERIC_BOUNDS[column]
    # fnlwgt's lower bound is exclusive; every other lower bound is inclusive.
    if column == "fnlwgt":
        if value <= low:
            return True
    elif value < low:
        return True
    return high is not None and value > high


def _finite_or_none(value: float) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def _numeric_summary(normalized: pd.DataFrame) -> dict[str, dict[str, float | None]]:
    summary: dict[str, dict[str, float | None]] = {}
    for column in NUMERIC_COLUMNS:
        values = normalized[column].astype("float64")
        valid = values[
            values.notna()
            & values.map(lambda value: math.isfinite(value) and not _is_out_of_range(column, value))
        ]
        entry: dict[str, float | None] = {}
        if valid.empty:
            entry.update({field: None for field in _SUMMARY_FIELDS})
        else:
            entry["count"] = float(valid.count())
            entry["mean"] = _finite_or_none(valid.mean())
            entry["median"] = _finite_or_none(valid.median())
            entry["min"] = _finite_or_none(valid.min())
            entry["max"] = _finite_or_none(valid.max())
            entry["std"] = _finite_or_none(valid.std()) if len(valid) > 1 else None
        summary[column] = entry
    return summary


def profile_data(
    df: pd.DataFrame, *, dataset: DatasetKind = "train", stage: ReportStage = "before",
) -> QualityReport:
    """Return a :class:`QualityReport` for ``df`` without modifying it.

    Counting rules follow the shared definitions in ``docs/公共接口说明.md`` §3:
    raw missing values are counted on the input cells, while duplicates,
    outliers and the numeric summary are computed on the normalized view.
    Parse failures are reported separately and are not extra missing values.
    """
    if dataset not in ("train", "test"):
        raise ValueError("dataset must be 'train' or 'test'")
    if stage not in ("before", "after"):
        raise ValueError("stage must be 'before' or 'after'")

    # Copy first: the caller's frame must not be touched, and normalize_frame
    # validates the fixed columns/labels/metadata on the same data.
    working = df.copy(deep=True)
    normalized, audit = normalize_frame(working)

    dtypes = {column: str(working[column].dtype) for column in FEATURE_COLUMNS}
    missing_by_column = {
        column: int(sum(_is_raw_missing(value) for value in working[column]))
        for column in FEATURE_COLUMNS
    }

    duplicate_view = normalized.loc[:, list(FEATURE_COLUMNS) + [TARGET_COLUMN]]
    duplicate_rows = int(len(duplicate_view) - len(duplicate_view.drop_duplicates(keep="first")))

    outlier_mask = pd.Series(False, index=normalized.index)
    outlier_cells = 0
    for column in NUMERIC_COLUMNS:
        values = normalized[column].astype("float64")
        invalid = values.map(
            lambda value: math.isfinite(value) and _is_out_of_range(column, value)
        )
        outlier_cells += int(invalid.sum())
        outlier_mask |= invalid

    warnings: list[str] = list(audit.warnings)
    parse_errors = int(audit.parse_error_cells)
    format_issues = int(audit.format_cells_changed)
    if parse_errors:
        warnings.append(
            f"{parse_errors} non-missing numeric cells could not be parsed and are treated as missing"
        )
    if outlier_cells:
        warnings.append(
            f"{outlier_cells} parsed numeric cells fall outside the fixed bounds"
        )

    return QualityReport(
        dataset=dataset,
        stage=stage,
        row_count=int(len(working)),
        dtypes=dtypes,
        missing_by_column=missing_by_column,
        duplicate_rows=duplicate_rows,
        outlier_cells=outlier_cells,
        outlier_rows=int(outlier_mask.sum()),
        format_issue_cells=format_issues,
        parse_error_cells=parse_errors,
        numeric_summary=_numeric_summary(normalized),
        warnings=warnings,
    )
