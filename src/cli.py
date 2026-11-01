"""Command-line entry point; orchestration belongs to C's run_pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .schema import ProjectError, RunResult

DEFAULT_TRAIN = "data/dirty/train_dirty.csv"
DEFAULT_TEST = "data/reference/test_reference.csv"


class PipelineUnavailable(RuntimeError):
    """The upstream pipeline has not been delivered yet."""


def run_requested_pipeline(train_path, test_path, *, mode, output_dir="outputs", seed=42):
    """Load the real pipeline lazily so the UI/help remain usable before delivery."""
    for name in (train_path, test_path):
        if not Path(name).is_file():
            raise FileNotFoundError(f"Input CSV does not exist: {name}")
    try:
        from .pipeline import run_pipeline
    except ModuleNotFoundError as exc:
        if exc.name == "src.pipeline":
            raise PipelineUnavailable("Member C has not delivered src/pipeline.py") from exc
        raise
    result = RunResult.model_validate(run_pipeline(
        train_path, test_path, mode=mode, output_dir=output_dir, seed=seed,
    ))
    if result.mode != mode:
        raise RuntimeError("Pipeline returned a different mode than requested")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("rules", "llm"), default="rules")
    parser.add_argument("--train", default=DEFAULT_TRAIN)
    parser.add_argument("--test", default=DEFAULT_TEST)
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    try:
        result = run_requested_pipeline(args.train, args.test, mode=args.mode,
                                        output_dir=args.output_dir, seed=args.seed)
    except (FileNotFoundError, ProjectError, PipelineUnavailable) as exc:
        print(f"Run failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Unexpected dependency errors must not expose credentials in messages.
        print(f"Run failed ({type(exc).__name__}); check member C's pipeline and dependencies.",
              file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    if result.status == "failed":
        print(f"Run failed: {result.error_code}; see events.jsonl in the output directory.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
