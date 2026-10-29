"""Shared, side-effect-free Adult table format normalization (contract 1.0).

Out-of-range *parsed* numbers are deliberately retained for the profiler.  The
cleaner is responsible for converting them to missing values before fitting.
"""

from __future__ import annotations

import math
import re
from numbers import Real

import pandas as pd

from .schema import (
    CATEGORICAL_COLUMNS, CLASS_LABELS, CSV_COLUMNS, FEATURE_COLUMNS,
    METADATA_COLUMNS, MISSING_TOKENS, NUMERIC_COLUMNS, TARGET_COLUMN,
    DataValidationError, NormalizationAudit, ALLOWED_SUFFIXES,
)

# Strict decimal/scientific notation: Python float() would otherwise accept
# nonstandard spellings such as "1_000". Whitelisted suffixes only.
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_PLAIN_NUMBER = re.compile(rf"^{_NUMBER}$")
_UNIT_NUMBERS = {
    column: re.compile(
        rf"^({_NUMBER})\s*(?:{'|'.join(re.escape(s) for s in suffixes)})$",
        re.IGNORECASE,
    )
    for column, suffixes in ALLOWED_SUFFIXES.items()
}


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in MISSING_TOKENS
    try:
        result = pd.isna(value)
        return bool(result) if isinstance(result, (bool, type(pd.NA))) and result is not pd.NA else False
    except (TypeError, ValueError):
        return False


def _validate_frame(df: pd.DataFrame) -> None:
    if not isinstance(df, pd.DataFrame):
        raise DataValidationError("Expected a pandas DataFrame")
    if not df.columns.is_unique:
        raise DataValidationError("Duplicate column names are not allowed")
    missing_columns = [c for c in CSV_COLUMNS if c not in df.columns]
    if missing_columns:
        raise DataValidationError(f"Missing required columns: {missing_columns}")
    extra_columns = [c for c in df.columns if c not in CSV_COLUMNS]
    if extra_columns:
        raise DataValidationError(f"Unexpected columns: {extra_columns}")
    for position, label in enumerate(df[TARGET_COLUMN]):
        if not isinstance(label, str) or label not in CLASS_LABELS:
            raise DataValidationError(f"Invalid income label at row position {position}: {label!r}")
    for column in METADATA_COLUMNS:
        for position, value in enumerate(df[column]):
            if not isinstance(value, str) or _is_missing(value):
                raise DataValidationError(f"Missing/invalid {column} at row position {position}")


def _numeric(value: object, column: str) -> tuple[float, bool, bool]:
    """Return (parsed-or-NaN, format_issue, parse_error)."""
    if _is_missing(value):
        return float("nan"), isinstance(value, str) and value != value.strip(), False
    if isinstance(value, bool):
        return float("nan"), True, True
    if isinstance(value, Real):
        number = float(value)
        if math.isfinite(number):
            return number, False, False
        return float("nan"), True, True
    if not isinstance(value, str):
        return float("nan"), True, True
    stripped = value.strip()
    changed = stripped != value
    if _PLAIN_NUMBER.fullmatch(stripped):
        text = stripped
    else:
        match = _UNIT_NUMBERS.get(column)
        unit_match = match.fullmatch(stripped) if match is not None else None
        if unit_match is None:
            return float("nan"), True, True
        text = unit_match.group(1)
        changed = True
    try:
        number = float(text)
    except (ValueError, OverflowError):
        return float("nan"), True, True
    if not math.isfinite(number):
        return float("nan"), True, True
    return number, changed, False


def normalize_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, NormalizationAudit]:
    """Normalize a copy; retain row order/index, labels, IDs, and numeric outliers.

    ``format_cells_changed`` counts a feature cell once if its string was
    trimmed, an allowed unit was removed, or numeric parsing failed. Parsing a
    plain numeric CSV string is not a format problem. Missing tokens are not
    parse errors. Calling this again on the output has zero new format issues.
    """
    _validate_frame(df)
    frame = df.loc[:, list(CSV_COLUMNS)].copy(deep=True)
    format_issues = 0
    parse_errors = 0

    for column in NUMERIC_COLUMNS:
        parsed = []
        for value in frame[column]:
            number, changed, failed = _numeric(value, column)
            parsed.append(number)
            format_issues += int(changed)
            parse_errors += int(failed)
        frame[column] = pd.Series(parsed, index=frame.index, dtype="float64").to_numpy()

    for column in CATEGORICAL_COLUMNS:
        normalized = []
        for value in frame[column]:
            if _is_missing(value):
                # A trimmed missing marker needs a format edit only if trimmed.
                format_issues += int(isinstance(value, str) and value != value.strip())
                normalized.append(None)
            elif isinstance(value, str):
                stripped = value.strip()
                format_issues += int(stripped != value)
                normalized.append(stripped)  # preserve case
            else:
                # Data was not a string; preserve a deterministic category.
                normalized.append(str(value))
        frame[column] = pd.Series(normalized, index=frame.index, dtype="object").to_numpy()

    return frame, NormalizationAudit(
        format_cells_changed=format_issues, parse_error_cells=parse_errors,
    )
