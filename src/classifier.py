"""Train one Adult logistic regression using only the fixed feature columns."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .schema import (
    CATEGORICAL_COLUMNS, CLASS_LABELS, CSV_COLUMNS, FEATURE_COLUMNS,
    METADATA_COLUMNS, MISSING_TOKENS, NUMERIC_BOUNDS, NUMERIC_COLUMNS,
    TARGET_COLUMN, ClassificationResult, DataValidationError,
)


def _validate_clean_frame(frame: pd.DataFrame, dataset: str) -> None:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise DataValidationError(f"{dataset}: expected a nonempty DataFrame")
    if not frame.columns.is_unique:
        raise DataValidationError(f"{dataset}: duplicate column names")
    missing = sorted(set(CSV_COLUMNS) - set(frame.columns))
    if missing:
        raise DataValidationError(f"{dataset}: missing columns: {', '.join(missing)}")
    if not frame[TARGET_COLUMN].isin(CLASS_LABELS).all():
        raise DataValidationError(f"{dataset}: invalid income label")
    for column in METADATA_COLUMNS + CATEGORICAL_COLUMNS:
        values = frame[column]
        valid = values.map(lambda x: isinstance(x, str) and bool(x.strip())
                           and x == x.strip() and x.casefold() not in MISSING_TOKENS)
        if not valid.all():
            raise DataValidationError(f"{dataset}: {column} contains missing or unnormalized text")
    for column in NUMERIC_COLUMNS:
        values = frame[column]
        if (not pd.api.types.is_numeric_dtype(values)
                or pd.api.types.is_bool_dtype(values)
                or pd.api.types.is_complex_dtype(values)):
            raise DataValidationError(f"{dataset}: {column} must already be numeric")
        numbers = values.to_numpy(dtype=float, na_value=np.nan)
        low, high = NUMERIC_BOUNDS[column]
        valid = np.isfinite(numbers) & (numbers >= low)
        if column == "fnlwgt":
            valid &= numbers > low
        if high is not None:
            valid &= numbers <= high
        if not valid.all():
            raise DataValidationError(f"{dataset}: {column} has missing or out-of-range values")
    if dataset == "train":
        if set(frame[TARGET_COLUMN]) != set(CLASS_LABELS):
            raise DataValidationError("train: both income classes are required")
        if frame.duplicated(subset=list(FEATURE_COLUMNS) + [TARGET_COLUMN]).any():
            raise DataValidationError("train: duplicate feature/label rows remain")


def _build_model(seed: int) -> Pipeline:
    preprocessing = ColumnTransformer([
        ("numeric", StandardScaler(), list(NUMERIC_COLUMNS)),
        ("categorical", OneHotEncoder(handle_unknown="ignore"), list(CATEGORICAL_COLUMNS)),
    ], remainder="drop")
    return Pipeline([
        ("preprocessing", preprocessing),
        ("classifier", LogisticRegression(random_state=seed, max_iter=2000)),
    ])


def train_and_evaluate(
    clean_train: pd.DataFrame, clean_test: pd.DataFrame, *,
    output_dir: str | Path, seed: int = 42,
) -> ClassificationResult:
    """Fit on training data, evaluate in CLASS_LABELS order, and save a PNG.

    Inputs are validated without normalization, imputation, or mutation. Metadata
    is used only for the group-disjointness check, never for fitting/prediction.
    """
    _validate_clean_frame(clean_train, "train")
    _validate_clean_frame(clean_test, "test")
    if set(clean_train["_group_id"]) & set(clean_test["_group_id"]):
        raise DataValidationError("train/test source groups overlap")
    model = _build_model(seed)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(clean_train.loc[:, list(FEATURE_COLUMNS)], clean_train[TARGET_COLUMN])
    predictions = model.predict(clean_test.loc[:, list(FEATURE_COLUMNS)])
    actual = clean_test[TARGET_COLUMN]
    matrix = confusion_matrix(actual, predictions, labels=list(CLASS_LABELS))
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    image_path = output / "confusion_matrix.png"
    figure = Figure(figsize=(5, 4), layout="constrained")
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    axes.imshow(matrix, cmap="Blues", vmin=0)
    axes.set(xticks=[0, 1], yticks=[0, 1], xticklabels=CLASS_LABELS,
             yticklabels=CLASS_LABELS, xlabel="Predicted label", ylabel="True label",
             title="Confusion matrix")
    for (row, column), value in np.ndenumerate(matrix):
        axes.text(column, row, str(value), ha="center", va="center",
                  color="white" if value > matrix.max() / 2 else "black")
    figure.savefig(image_path, dpi=160)
    return ClassificationResult(
        accuracy=float(accuracy_score(actual, predictions)),
        macro_f1=float(f1_score(actual, predictions, labels=list(CLASS_LABELS),
                               average="macro", zero_division=0)),
        test_rows=len(clean_test),
        class_counts_test={label: int((actual == label).sum()) for label in CLASS_LABELS},
        confusion_matrix=matrix.tolist(), confusion_matrix_path=str(image_path),
    )
