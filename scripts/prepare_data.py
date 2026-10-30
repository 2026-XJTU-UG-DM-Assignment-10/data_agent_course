"""Build the formal Adult dataset for the course project.

Fixed command::

    python scripts/prepare_data.py --seed 42 --sample-size 10000

The script obtains the real UCI Adult ``adult.data`` file (or uses a manually
placed copy), parses and validates the labels, draws a fixed-seed sample, splits
it by normalized feature-group signature, injects the four problem types into the
training split only, and writes the public CSV/manifest paths. It never generates
substitute data: when neither the local file nor the download is available it
stops with manual instructions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.normalization import normalize_frame  # noqa: E402
from src.schema import (  # noqa: E402
    CATEGORICAL_COLUMNS, FEATURE_COLUMNS, MISSING_TOKENS, NUMERIC_COLUMNS,
    TARGET_COLUMN,
)

SOURCE_URL = "https://archive.ics.uci.edu/static/public/2/adult.zip"
SOURCE_PAGE = "https://archive.ics.uci.edu/dataset/2/adult"
LICENSE = "CC BY 4.0"
CITATION = (
    "Becker, B. and Kohavi, R. (1996). Adult. UCI Machine Learning Repository. "
    "https://doi.org/10.24432/C5XW20"
)
RAW_COLUMNS = (*FEATURE_COLUMNS, TARGET_COLUMN)

RAW_PATH = ROOT / "data" / "raw" / "adult.data"
ZIP_PATH = ROOT / "data" / "raw" / "adult.zip"
TRAIN_REFERENCE = ROOT / "data" / "reference" / "train_reference.csv"
TEST_REFERENCE = ROOT / "data" / "reference" / "test_reference.csv"
TRAIN_DIRTY = ROOT / "data" / "dirty" / "train_dirty.csv"
SPLIT_MANIFEST = ROOT / "data" / "manifests" / "split_manifest.csv"
INJECTION_MANIFEST = ROOT / "data" / "manifests" / "injection_manifest.csv"
PREPARATION_SUMMARY = ROOT / "data" / "manifests" / "preparation_summary.json"

# Default construction parameters from the task book; proportions are not
# acceptance thresholds.
MISSING_RATE = 0.05
DUPLICATE_RATE = 0.02
OUTLIER_RATE = 0.01
FORMAT_RATE = 0.03
TRAIN_SHARE = 0.70


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_missing_value(value: object) -> bool:
    """Public missing-token definition; parse failures are not counted here."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in MISSING_TOKENS
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if isinstance(result, bool) else False


def ensure_raw_file(raw_path: Path, zip_path: Path) -> str:
    """Return a provenance string, downloading the official archive if needed."""
    if raw_path.is_file() and raw_path.stat().st_size > 0:
        return "existing local file (not re-downloaded)"

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "python-urllib/adult-prep"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
    except (urllib.error.URLError, OSError) as exc:
        raise SystemExit(
            "Could not download UCI Adult automatically ({0}).\n"
            "Download {1} manually, extract it, and place adult.data at:\n  {2}\n"
            "Then run this script again. No synthetic data will be generated."
            .format(exc, SOURCE_URL, raw_path)
        )
    zip_path.write_bytes(payload)
    with zipfile.ZipFile(zip_path) as archive:
        members = [name for name in archive.namelist() if name.endswith("adult.data")]
        if not members:
            raise SystemExit(f"Archive {zip_path} does not contain adult.data")
        raw_path.write_bytes(archive.read(members[0]))
    return f"downloaded from {SOURCE_URL}"


def read_raw(raw_path: Path) -> tuple[pd.DataFrame, dict]:
    """Parse the official file into string cells and record label exclusions."""
    records, invalid_labels, malformed = [], 0, 0
    with raw_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if not row or all(not cell.strip() for cell in row):
                continue
            if len(row) != len(RAW_COLUMNS):
                malformed += 1
                continue
            values = [cell.strip() for cell in row]
            label = values[-1].rstrip(".")
            if label not in ("<=50K", ">50K"):
                invalid_labels += 1
                continue
            values[-1] = label
            records.append([str(value) for value in values])

    frame = pd.DataFrame(records, columns=list(RAW_COLUMNS), dtype="object")
    return frame, {
        "raw_records": int(len(records) + invalid_labels + malformed),
        "excluded_invalid_label": invalid_labels,
        "excluded_malformed": malformed,
        "reference_pool": int(len(frame)),
    }


def canonical_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return "" if math.isnan(value) else repr(value)
    return str(value)


def compute_group_ids(frame: pd.DataFrame) -> list[str]:
    """Stable SHA-256 signature over the normalized 14-feature view."""
    probe = frame.loc[:, list(RAW_COLUMNS)].copy()
    probe["_source_id"] = "probe"
    probe["_group_id"] = "probe"
    normalized, _ = normalize_frame(probe.loc[:, list(RAW_COLUMNS) + ["_source_id", "_group_id"]])
    groups = []
    for position in range(len(normalized)):
        signature = [canonical_cell(normalized.iat[position, normalized.columns.get_loc(column)])
                     for column in FEATURE_COLUMNS]
        payload = json.dumps(signature, ensure_ascii=False, separators=(",", ":"))
        groups.append("G" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16])
    return groups


def split_by_group(frame: pd.DataFrame, rng: random.Random) -> tuple[pd.Series, dict]:
    """Assign whole groups to one split so train/test group sets never intersect."""
    group_ids = frame["_group_id"].tolist()
    sizes: dict[str, int] = {}
    for group in group_ids:
        sizes[group] = sizes.get(group, 0) + 1
    unique_groups = sorted(sizes)
    rng.shuffle(unique_groups)
    target_train = int(round(TRAIN_SHARE * len(frame)))
    train_groups: list[str] = []
    train_rows = 0
    for group in unique_groups:
        if train_rows < target_train:
            train_groups.append(group)
            train_rows += sizes[group]
    train_set = set(train_groups)
    split = pd.Series(["train" if group in train_set else "test" for group in group_ids],
                      index=frame.index, dtype="object")
    stats = {
        "train_rows": int((split == "train").sum()),
        "test_rows": int((split == "test").sum()),
        "train_groups": len(train_groups),
        "test_groups": len(unique_groups) - len(train_groups),
    }
    return split, stats


def choose_cells(dirty: pd.DataFrame, columns, used: set[int], rng: random.Random,
                 count: int) -> list[tuple[int, str]]:
    """Pick (row position, column) pairs that are non-missing and not yet used."""
    candidates = [
        (position, column)
        for column in columns
        for position in range(len(dirty))
        if (position, dirty.columns.get_loc(column)) not in used
        and not is_missing_value(dirty.iat[position, dirty.columns.get_loc(column)])
    ]
    if len(candidates) < count:
        raise SystemExit(
            f"Not enough non-missing cells for {count} injections: {len(candidates)} available"
        )
    return rng.sample(candidates, count)


def inject_problems(train_frame: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, list[dict], dict]:
    """Inject the four problem types; duplicates are appended last."""
    dirty = train_frame.reset_index(drop=True).copy()
    rng = random.Random(seed)
    injections: list[dict] = []
    used: set[tuple[int, int]] = set()

    def record(position: int, column: str, kind: str, old: str, new: str) -> None:
        injections.append({
            "_source_id": str(dirty.at[position, "_source_id"]),
            "field": column,
            "problem_type": kind,
            "old_value": str(old),
            "new_value": str(new),
        })

    # 1. Outliers: about 1% of training rows, one invalid cell per chosen row.
    outlier_target = int(round(OUTLIER_RATE * len(dirty)))
    row_order = list(range(len(dirty)))
    rng.shuffle(row_order)
    for position in row_order[:outlier_target]:
        column = rng.choice(["age", "hours_per_week"])
        value = rng.choice([-5, 999]) if column == "age" else rng.choice([0, 999])
        old = dirty.at[position, column]
        dirty.at[position, column] = str(value)
        used.add((position, dirty.columns.get_loc(column)))
        record(position, column, "outlier", old, value)

    # 2. Missing tokens: about 5% of the still non-missing feature cells.
    non_missing_cells = sum(
        not is_missing_value(dirty.iat[position, dirty.columns.get_loc(column)])
        for column in FEATURE_COLUMNS for position in range(len(dirty))
    )
    missing_target = int(round(MISSING_RATE * non_missing_cells))
    for position, column in choose_cells(dirty, FEATURE_COLUMNS, used, rng, missing_target):
        old = dirty.at[position, column]
        dirty.at[position, column] = "?"
        used.add((position, dirty.columns.get_loc(column)))
        record(position, column, "missing", old, "?")

    # 3. Format noise: about 3% of non-missing numeric cells (spaces or units).
    numeric_non_missing = sum(
        not is_missing_value(dirty.iat[position, dirty.columns.get_loc(column)])
        for column in NUMERIC_COLUMNS for position in range(len(dirty))
    )
    format_target = int(round(FORMAT_RATE * numeric_non_missing))
    for position, column in choose_cells(dirty, NUMERIC_COLUMNS, used, rng, format_target):
        old = dirty.at[position, column]
        if column == "age" and rng.random() < 0.5:
            new = f"{old} years"
        elif column == "hours_per_week" and rng.random() < 0.5:
            new = f"{old} hours"
        else:
            new = f" {old} "
        dirty.at[position, column] = new
        used.add((position, dirty.columns.get_loc(column)))
        record(position, column, "format", old, new)

    # 4. Duplicates last, so copies carry every injected problem of their source.
    duplicate_target = int(round(DUPLICATE_RATE * len(dirty)))
    duplicate_positions = rng.sample(range(len(dirty)), duplicate_target)
    duplicates = dirty.iloc[duplicate_positions].copy()
    for position in duplicate_positions:
        record(position, "(whole_row)", "duplicate", "original_row", "duplicated_row")
    dirty = pd.concat([dirty, duplicates], ignore_index=True)

    actual = {
        "outlier_rows": outlier_target,
        "missing_cells": missing_target,
        "format_cells": format_target,
        "duplicate_rows": duplicate_target,
    }
    return dirty, injections, actual


def write_csv(frame: pd.DataFrame, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return {"rows": int(len(frame)), "sha256": sha256_file(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample-size", type=int, default=10000)
    parser.add_argument("--raw-file", type=Path, default=RAW_PATH,
                        help="Manually downloaded adult.data location")
    args = parser.parse_args()
    if args.sample_size <= 0:
        parser.error("--sample-size must be positive")

    provenance = ensure_raw_file(args.raw_file, ZIP_PATH)
    raw_sha256 = sha256_file(args.raw_file)
    pool, parse_stats = read_raw(args.raw_file)
    if len(pool) < args.sample_size:
        raise SystemExit(
            f"Reference pool has {len(pool)} usable records, fewer than --sample-size {args.sample_size}"
        )

    # Fixed-seed sampling; sorted positions keep the original file order.
    sample_rng = random.Random(args.seed)
    positions = sorted(sample_rng.sample(range(len(pool)), args.sample_size))
    reference = pool.iloc[positions].reset_index(drop=True).copy()
    reference["_source_id"] = [f"S{position + 1:06d}" for position in positions]

    reference["_group_id"] = compute_group_ids(reference)
    split, split_stats = split_by_group(reference, sample_rng)
    reference["_group_id"] = reference["_group_id"].astype("object")
    reference.loc[:, "_group_id"] = reference["_group_id"].astype(str)

    train_ref = reference.loc[split == "train", list(RAW_COLUMNS) + ["_source_id", "_group_id"]].reset_index(drop=True)
    test_ref = reference.loc[split == "test", list(RAW_COLUMNS) + ["_source_id", "_group_id"]].reset_index(drop=True)

    train_groups = set(train_ref["_group_id"])
    test_groups = set(test_ref["_group_id"])
    if train_groups & test_groups:
        raise SystemExit("Train/test group ids intersect; refusing to write formal data")
    if len(train_ref) <= 5000:
        raise SystemExit(f"Training split has {len(train_ref)} rows; the course requires more than 5000")

    dirty, injections, actual = inject_problems(train_ref, args.seed)

    outputs = {
        "data/reference/train_reference.csv": write_csv(train_ref, TRAIN_REFERENCE),
        "data/reference/test_reference.csv": write_csv(test_ref, TEST_REFERENCE),
        "data/dirty/train_dirty.csv": write_csv(dirty, TRAIN_DIRTY),
    }

    split_frame = pd.DataFrame({
        "_source_id": reference["_source_id"],
        "_group_id": reference["_group_id"],
        "split": split,
    })
    outputs["data/manifests/split_manifest.csv"] = write_csv(split_frame, SPLIT_MANIFEST)
    injection_frame = pd.DataFrame(injections, columns=["_source_id", "field", "problem_type", "old_value", "new_value"])
    outputs["data/manifests/injection_manifest.csv"] = write_csv(injection_frame, INJECTION_MANIFEST)

    summary = {
        "status": "ready",
        "workflow_version": "2.0",
        "contract_version": "1.0",
        "role": "A",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/prepare_data.py",
        "command": f"python scripts/prepare_data.py --seed {args.seed} --sample-size {args.sample_size}",
        "source": {
            "name": "UCI Adult (Census Income)",
            "page": SOURCE_PAGE,
            "download_url": SOURCE_URL,
            "license": LICENSE,
            "citation": CITATION,
            "provenance": provenance,
            "raw_path": "data/raw/adult.data",
            "raw_sha256": raw_sha256,
            "raw_bytes": args.raw_file.stat().st_size,
        },
        "parse": parse_stats,
        "sample": {"seed": args.seed, "sample_size": args.sample_size, "sampled_records": len(reference)},
        "split": {
            "method": "sha256 over normalized 14-feature signature, whole groups assigned to one split",
            "train_share_target": TRAIN_SHARE,
            **split_stats,
            "group_overlap": 0,
        },
        "injection": {
            "parameters": {
                "missing_rate_of_non_missing_cells": MISSING_RATE,
                "duplicate_rate_of_train_rows": DUPLICATE_RATE,
                "outlier_rate_of_train_rows": OUTLIER_RATE,
                "format_rate_of_non_missing_numeric_cells": FORMAT_RATE,
            },
            "actual": actual,
            "train_dirty_rows": int(len(dirty)),
            "test_rows_injected": 0,
        },
        "outputs": outputs,
        "checks": {
            "reference_records": int(len(reference)),
            "train_rows_gt_5000": bool(len(train_ref) > 5000),
            "train_test_group_ids_disjoint": True,
            "duplicates_keep_source_id": True,
            "test_reference_has_no_injection": True,
            "raw_file_preserved": True,
        },
        "notes": [
            "Reference data may still contain native missing values; it is not a fully clean ground truth.",
            "Manifests are construction audits only; they must not be fed to the model or classifier.",
            "Injected problems touch feature cells only; income and metadata are never modified.",
        ],
    }
    PREPARATION_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    PREPARATION_SUMMARY.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(json.dumps({
        "status": "prepared",
        "reference_rows": len(reference),
        "train_rows": int(len(train_ref)),
        "test_rows": int(len(test_ref)),
        "train_dirty_rows": int(len(dirty)),
        "injections": actual,
        "group_ids_disjoint": True,
        "summary": "data/manifests/preparation_summary.json",
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
