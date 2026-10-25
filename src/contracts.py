"""Signature-only protocols for collaboration, not business implementations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

from .schema import (
    ClassificationResult, CleaningAudit, CleaningPlan, CleaningState,
    DatasetKind, LLMReply, Mode, NormalizationAudit, QualityReport,
    ReportStage, RunResult,
)

if TYPE_CHECKING:
    import pandas as pd

EventSink = Callable[[str, dict[str, Any]], None]


class LLMClientProtocol(Protocol):
    def generate_plan(
        self, summary: dict[str, Any], *, feedback: str | None = None,
    ) -> LLMReply: ...


class NormalizeFrameProtocol(Protocol):
    def __call__(self, df: pd.DataFrame) -> tuple[pd.DataFrame, NormalizationAudit]: ...


class ProfileDataProtocol(Protocol):
    def __call__(
        self, df: pd.DataFrame, *, dataset: DatasetKind = "train",
        stage: ReportStage = "before",
    ) -> QualityReport: ...


class GetCleaningPlanProtocol(Protocol):
    def __call__(
        self, train_report: QualityReport, *, mode: Mode,
        llm_client: LLMClientProtocol | None = None,
        event_sink: EventSink | None = None,
    ) -> CleaningPlan: ...


class CleanTrainingDataProtocol(Protocol):
    def __call__(
        self, train_df: pd.DataFrame, plan: CleaningPlan,
    ) -> tuple[pd.DataFrame, CleaningState, CleaningAudit]: ...


class TransformTestDataProtocol(Protocol):
    def __call__(
        self, test_df: pd.DataFrame, cleaning_state: CleaningState,
    ) -> tuple[pd.DataFrame, CleaningAudit]: ...


class TrainAndEvaluateProtocol(Protocol):
    def __call__(
        self, clean_train: pd.DataFrame, clean_test: pd.DataFrame, *,
        output_dir: str | Path, seed: int = 42,
    ) -> ClassificationResult: ...


class RunPipelineProtocol(Protocol):
    def __call__(
        self, train_path: str | Path, test_path: str | Path, *,
        mode: Mode, output_dir: str | Path = "outputs", seed: int = 42,
        llm_client: LLMClientProtocol | None = None,
    ) -> RunResult: ...
