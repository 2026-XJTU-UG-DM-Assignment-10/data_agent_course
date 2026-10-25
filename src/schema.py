"""Public contract v1.0. No cleaning, modelling, or HTTP implementation here."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTRACT_VERSION = "1.0"
RANDOM_SEED = 42
TARGET_COLUMN = "income"
FEATURE_COLUMNS = (
    "age", "workclass", "fnlwgt", "education", "education_num",
    "marital_status", "occupation", "relationship", "race", "sex",
    "capital_gain", "capital_loss", "hours_per_week", "native_country",
)
NUMERIC_COLUMNS = (
    "age", "fnlwgt", "education_num", "capital_gain", "capital_loss",
    "hours_per_week",
)
CATEGORICAL_COLUMNS = tuple(c for c in FEATURE_COLUMNS if c not in NUMERIC_COLUMNS)
METADATA_COLUMNS = ("_source_id", "_group_id")
CSV_COLUMNS = FEATURE_COLUMNS + (TARGET_COLUMN,) + METADATA_COLUMNS
CLASS_LABELS = ("<=50K", ">50K")
MISSING_TOKENS = frozenset({"", "?", "na", "n/a", "nan", "null", "none"})
CATEGORY_FILL_VALUE = "Unknown"
NUMERIC_BOUNDS = {
    "age": (17.0, 120.0),
    "fnlwgt": (0.0, None),  # lower bound is exclusive for this field only
    "education_num": (1.0, 16.0),
    "capital_gain": (0.0, None),
    "capital_loss": (0.0, None),
    "hours_per_week": (1.0, 168.0),
}
ALLOWED_SUFFIXES = {
    "age": ("years", "year"),
    "hours_per_week": ("hours", "hour", "h"),
}
CLEANING_STEPS = (
    "normalize_format", "drop_duplicates", "mark_invalid", "impute_missing",
)

Mode = Literal["rules", "llm"]
DatasetKind = Literal["train", "test"]
ReportStage = Literal["before", "after"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    contract_version: Literal["1.0"] = CONTRACT_VERSION


class NormalizationAudit(ContractModel):
    format_cells_changed: int = Field(default=0, ge=0)
    parse_error_cells: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)


class QualityReport(ContractModel):
    dataset: DatasetKind
    stage: ReportStage
    row_count: int = Field(ge=0)
    feature_count: Literal[14] = 14
    dtypes: dict[str, str] = Field(default_factory=dict)
    missing_by_column: dict[str, int] = Field(default_factory=dict)
    duplicate_rows: int = Field(default=0, ge=0)
    outlier_cells: int = Field(default=0, ge=0)
    outlier_rows: int = Field(default=0, ge=0)
    format_issue_cells: int = Field(default=0, ge=0)
    parse_error_cells: int = Field(default=0, ge=0)
    numeric_summary: dict[str, dict[str, float | None]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class CleaningPlan(ContractModel):
    mode: Mode
    steps: tuple[str, ...] = CLEANING_STEPS
    numeric_imputation: Literal["mean", "median"]
    categorical_imputation: Literal["most_frequent", "constant"]
    categorical_fill_value: Literal["Unknown"] = CATEGORY_FILL_VALUE
    reason_numeric: str = Field(min_length=1)
    reason_categorical: str = Field(min_length=1)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != CLEANING_STEPS:
            raise ValueError("steps must match the four fixed steps in order")
        return value


class CleaningState(ContractModel):
    plan: CleaningPlan
    numeric_fill_values: dict[str, float]
    categorical_fill_values: dict[str, str]
    feature_columns: tuple[str, ...] = FEATURE_COLUMNS

    @model_validator(mode="after")
    def validate_columns(self) -> CleaningState:
        if self.feature_columns != FEATURE_COLUMNS:
            raise ValueError("feature_columns must match the fixed Adult schema")
        if set(self.numeric_fill_values) != set(NUMERIC_COLUMNS):
            raise ValueError("numeric_fill_values must contain all six numeric columns")
        if set(self.categorical_fill_values) != set(CATEGORICAL_COLUMNS):
            raise ValueError("categorical_fill_values must contain all eight category columns")
        return self


class CleaningAudit(ContractModel):
    dataset: DatasetKind
    input_rows: int = Field(ge=0)
    output_rows: int = Field(ge=0)
    format_cells_changed: int = Field(default=0, ge=0)
    parse_error_cells: int = Field(default=0, ge=0)
    invalid_cells_set_missing: int = Field(default=0, ge=0)
    missing_cells_filled: int = Field(default=0, ge=0)
    duplicate_rows_removed_before_fill: int = Field(default=0, ge=0)
    duplicate_rows_removed_after_fill: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_row_counts(self) -> CleaningAudit:
        removed = (
            self.duplicate_rows_removed_before_fill
            + self.duplicate_rows_removed_after_fill
        )
        if self.input_rows - self.output_rows != removed:
            raise ValueError("row reduction must equal the number of removed duplicates")
        if self.dataset == "test" and removed:
            raise ValueError("test rows must never be removed")
        return self


class ClassificationResult(ContractModel):
    accuracy: float = Field(ge=0, le=1)
    macro_f1: float = Field(ge=0, le=1)
    test_rows: int = Field(gt=0)
    class_counts_test: dict[str, int]
    labels: tuple[Literal["<=50K"], Literal[">50K"]] = CLASS_LABELS
    confusion_matrix: list[list[int]]
    confusion_matrix_path: str

    @model_validator(mode="after")
    def validate_confusion_matrix(self) -> ClassificationResult:
        matrix = self.confusion_matrix
        if len(matrix) != 2 or any(len(row) != 2 for row in matrix):
            raise ValueError("confusion_matrix must be 2x2")
        if any(value < 0 for row in matrix for value in row):
            raise ValueError("confusion_matrix counts must be nonnegative")
        if sum(map(sum, matrix)) != self.test_rows:
            raise ValueError("confusion_matrix total must equal test_rows")
        if set(self.class_counts_test) != set(CLASS_LABELS):
            raise ValueError("class_counts_test must contain both fixed labels")
        for index, label in enumerate(CLASS_LABELS):
            if sum(matrix[index]) != self.class_counts_test[label]:
                raise ValueError("class_counts_test must equal matrix row totals")
        return self


class LLMReply(ContractModel):
    text: str
    provider: str
    model: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)
    currency: str | None = None
    cost_source: str | None = None


class RunEvent(ContractModel):
    run_id: str
    sequence: int = Field(ge=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: Mode
    name: str
    status: Literal["started", "succeeded", "failed", "info"]
    duration_ms: float | None = Field(default=None, ge=0)
    data: dict[str, Any] = Field(default_factory=dict)


class RunResult(ContractModel):
    run_id: str
    status: Literal["succeeded", "failed"]
    mode: Mode
    output_dir: str
    artifacts: dict[str, str] = Field(default_factory=dict)
    metrics: ClassificationResult | None = None
    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_status(self) -> RunResult:
        if self.status == "succeeded" and (
            self.metrics is None or self.error_code is not None or self.error_message is not None
        ):
            raise ValueError("successful run needs metrics and no error")
        if self.status == "failed" and (not self.error_code or not self.error_message):
            raise ValueError("failed run needs error_code and error_message")
        return self


class ProjectError(Exception):
    code = "project_error"


class DataValidationError(ProjectError):
    code = "invalid_data"


class PlanValidationError(ProjectError):
    code = "invalid_plan"


class ModelCallError(ProjectError):
    code = "model_call_failed"
