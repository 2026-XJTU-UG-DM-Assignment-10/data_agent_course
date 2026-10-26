"""Local collaboration gates. A passing module gate is not final course acceptance."""

from __future__ import annotations

import argparse
import ast
import csv
import fnmatch
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_hash(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def local_path(value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("Evidence paths must be nonempty project-relative paths")
    result = (ROOT / value).resolve()
    if not result.is_relative_to(ROOT):
        raise ValueError("Evidence path escapes the project")
    return result


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("utf-8").rstrip("\r\n")


def receipt_errors(role: str, claim: str, reference: str) -> list[str]:
    errors = []
    try:
        path = local_path(reference)
        if not reference.replace("\\", "/").startswith(f"evidence/{role}/") or path.suffix != ".json" or not path.is_file():
            return [f"Use a committed evidence/{role}/*.json receipt for {claim}"]
        if path.stat().st_size > 200_000:
            return ["Evidence receipts must be small sanitized summaries"]
        content = path.read_text(encoding="utf-8")
        receipt = json.loads(content)
        if not isinstance(receipt, dict):
            return ["Evidence receipt must be an object"]
        expected = {"workflow_version": "2.0", "contract_version": "1.0", "role": role, "scope": claim, "status": "passed"}
        for key, value in expected.items():
            if receipt.get(key) != value:
                errors.append(f"Receipt {reference}: {key} must be {value}")
        if not isinstance(receipt.get("command"), str) or not receipt["command"].strip() or not isinstance(receipt.get("summary"), dict) or not receipt["summary"]:
            errors.append(f"Receipt needs actual time, command and summary: {reference}")
        try:
            if datetime.fromisoformat(receipt.get("checked_at", "")).tzinfo is None:
                errors.append(f"Receipt timestamp must include timezone: {reference}")
        except (TypeError, ValueError):
            errors.append(f"Receipt timestamp must be a real ISO timestamp: {reference}")
        if not isinstance(receipt.get("uses_test_doubles"), bool):
            errors.append(f"Receipt must declare uses_test_doubles: {reference}")
        if claim != "fixtures" and receipt.get("uses_test_doubles") is not False:
            errors.append(f"Real verification cannot use test doubles: {reference}")
        forbidden = {"api_key", "llm_api_key", "authorization", "access_token", "password", "cookie", "secret", "prompt", "raw_response"}
        def visit(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key.casefold() in forbidden:
                        errors.append(f"Sensitive/raw fields must remain in local outputs: {reference}")
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(receipt)
        if re.search(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{20,})\b", content):
            errors.append(f"Possible credential in public receipt: {reference}")
        if not isinstance(receipt.get("artifacts", []), list):
            errors.append(f"Receipt artifacts must be a list: {reference}")
        else:
            for artifact in receipt.get("artifacts", []):
                local_path(artifact)  # Raw outputs may not exist on another member's machine.
    except (OSError, ValueError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def record_errors(role: str, record: dict, config: dict, *, ready: bool = False) -> list[str]:
    if not isinstance(record, dict):
        return [f"Role {role} handoff must be a JSON object"]
    errors = []
    expected = {"workflow_version": "2.0", "contract_version": "1.0", "role": role, "branch": config["branch"]}
    for key, value in expected.items():
        if record.get(key) != value:
            errors.append(f"handoff {key} must be {value}")
    if record.get("status") not in {"not_started", "working", "blocked", "ready_for_review"}:
        errors.append("Invalid handoff status")
    for key in ("completed", "changed_files", "blockers"):
        if not isinstance(record.get(key), list):
            errors.append(f"handoff {key} must be a list")
    if record.get("last_gate") is not None and not isinstance(record["last_gate"], dict):
        errors.append("last_gate must be null or an object")
    verification = record.get("verification", {})
    if not isinstance(verification, dict):
        return errors + ["verification must be an object"]
    for claim in ("fixtures", "formal_data", "real_llm", "end_to_end"):
        item = verification.get(claim, {})
        if not isinstance(item, dict):
            errors.append(f"Verification entry must be an object: {claim}")
            continue
        if item.get("status") not in {"not_run", "passed", "failed", "blocked"}:
            errors.append(f"Invalid verification status: {claim}")
        if not isinstance(item.get("evidence"), list):
            errors.append(f"Evidence must be a list: {claim}")
        if ready and item.get("status") == "passed":
            if not item.get("evidence"):
                errors.append(f"Passed claim needs evidence: {claim}")
            for evidence in item.get("evidence", []) if isinstance(item.get("evidence"), list) else []:
                errors.extend(receipt_errors(role, claim, evidence))
    if ready:
        if not record.get("completed"):
            errors.append("Describe completed work before submitting")
        if record.get("blockers") or record.get("status") == "blocked":
            errors.append("Resolve blockers or keep this delivery blocked")
        for claim in config["required_claims"]:
            if not isinstance(verification.get(claim), dict) or verification[claim].get("status") != "passed":
                errors.append(f"Required verification not passed: {claim}")
    return errors


def foundation_errors(manifest: dict) -> list[str]:
    from pydantic import ValidationError
    from scripts.summarize_ai_usage import load_records
    from src import schema

    errors = []
    load_records(ROOT)  # Empty starter logs are valid; final role delivery needs real records.
    if manifest.get("workflow_version") != "2.0" or manifest.get("contract_version") != "1.0":
        errors.append("Unexpected workflow or contract version")
    if set(manifest.get("roles", {})) != set("ABCD"):
        errors.append("Manifest must contain exactly roles A-D")
    frozen = read_json("collaboration/contract_hashes.json")
    for path in manifest["frozen_files"]:
        if frozen.get("files", {}).get(path) != text_hash(ROOT / path):
            errors.append(f"Frozen contract changed: {path}")
    for role, config in manifest["roles"].items():
        for path in [config["task"], config["prompt"], config["handoff"], *config["offline_inputs"]]:
            if not (ROOT / path).is_file():
                errors.append(f"Missing collaboration input: {path}")
        if (ROOT / config["handoff"]).is_file():
            errors.extend(record_errors(role, read_json(config["handoff"]), config))
    fixture_manifest = read_json("examples/fixtures_manifest.json")
    if fixture_manifest.get("is_experiment") is not False:
        errors.append("Fixture manifest must explicitly mark data as non-experimental")
    for item in fixture_manifest["files"]:
        path = ROOT / item["file"]
        if not path.is_file():
            errors.append(f"Missing fixture: {item['file']}")
            continue
        if item["kind"] == "json":
            try:
                getattr(schema, item["model"]).model_validate_json(path.read_text(encoding="utf-8"))
                if item.get("expect_invalid"):
                    errors.append(f"Invalid-plan fixture was accepted: {item['file']}")
            except ValidationError:
                if not item.get("expect_invalid"):
                    errors.append(f"Fixture does not match public model: {item['file']}")
        elif item["kind"] in {"csv", "csv_clean"}:
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if tuple(reader.fieldnames or ()) != schema.CSV_COLUMNS:
                    errors.append(f"CSV columns differ from shared schema: {item['file']}")
                rows = list(reader)
            if item["kind"] == "csv_clean":
                for row in rows:
                    if any(row[column].strip().casefold() in schema.MISSING_TOKENS for column in schema.FEATURE_COLUMNS):
                        errors.append(f"Missing value in clean fixture: {item['file']}")
                    for column in schema.NUMERIC_COLUMNS:
                        value = float(row[column])
                        low, high = schema.NUMERIC_BOUNDS[column]
                        if not math.isfinite(value) or value < low or (column == "fnlwgt" and value == 0) or (high is not None and value > high):
                            errors.append(f"Invalid numeric value in clean fixture: {item['file']}:{column}")
    return errors


def changed_files() -> list[str]:
    paths = set()
    for args in (
        ("diff", "--name-only", "-z", "origin/main...HEAD"),
        ("diff", "--name-only", "-z", "HEAD"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        paths.update(path for path in git(*args).split("\0") if path)
    return sorted(paths)


def signature_errors(config: dict) -> list[str]:
    errors = []
    for entry in config["entrypoints"]:
        path = ROOT / entry["file"]
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == entry["name"]]
        if len(functions) != 1:
            errors.append(f"Expected one top-level function: {entry['file']}:{entry['name']}")
            continue
        arguments = functions[0].args
        if [arg.arg for arg in arguments.posonlyargs + arguments.args] != entry["args"] or [arg.arg for arg in arguments.kwonlyargs] != entry["kwonly"] or arguments.vararg or arguments.kwarg:
            errors.append(f"Public signature differs: {entry['file']}:{entry['name']}")
        if arguments.defaults:
            errors.append(f"Positional parameters must remain required: {entry['name']}")
        expected_defaults = entry.get("kw_defaults", {})
        for parameter, default in zip(arguments.kwonlyargs, arguments.kw_defaults):
            try:
                if parameter.arg in expected_defaults:
                    if default is None or ast.literal_eval(default) != expected_defaults[parameter.arg]:
                        errors.append(f"Keyword default differs: {entry['name']}:{parameter.arg}")
                elif default is not None:
                    errors.append(f"Keyword must remain required: {entry['name']}:{parameter.arg}")
            except (ValueError, TypeError):
                errors.append(f"Keyword default must be a fixed literal: {entry['name']}:{parameter.arg}")
    return errors


def run_role(role: str, manifest: dict, *, integration: bool, submit: bool) -> tuple[int, dict]:
    config = manifest["roles"][role]
    report = {"role": role, "status": "not_ready", "scope": "module review only", "errors": []}
    errors = report["errors"]
    branch = git("branch", "--show-current")
    if integration:
        if branch != "main":
            errors.append("Integration checks must run on main")
        changes = []
    else:
        if branch != config["branch"]:
            errors.append(f"Expected branch {config['branch']}; current branch is {branch}. No automatic switch was performed.")
        git("rev-parse", "--verify", "origin/main")
        changes = changed_files()
        for path in changes:
            if not any(fnmatch.fnmatchcase(path, pattern) for pattern in config["owned_paths"]):
                errors.append(f"File outside role {role} ownership: {path}")
    for path in config["required_files"]:
        if not (ROOT / path).is_file():
            errors.append(f"Missing role deliverable: {path}")
    record = read_json(config["handoff"])
    errors.extend(record_errors(role, record, config))
    errors.extend(signature_errors(config))
    if submit or integration:
        from scripts.summarize_ai_usage import load_records
        try:
            load_records(ROOT, role, require_records=True)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            errors.append(f"AI usage log not ready: {exc}")
    if errors:
        return 2, report
    receipt_snapshots = {str(path): path.read_bytes() for path in (ROOT / "evidence" / role).glob("*.json")}
    command = [sys.executable, config["self_check"]]
    if integration:
        command.append("--integration")
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    check_command = f"python {config['self_check']}" + (" --integration" if integration else "")
    report["self_check"] = {"command": check_command, "exit_code": process.returncode, "stdout_tail": process.stdout[-6000:], "stderr_tail": process.stderr[-3000:]}
    if process.returncode:
        pending = process.returncode == 2
        errors.append("Role self-check is not ready; see missing inputs" if pending else "Role self-check failed; fix your own module")
        report["status"] = "not_ready" if pending else "failed"
        return (2 if pending else 1), report
    for path in manifest["frozen_files"]:
        if read_json("collaboration/contract_hashes.json")["files"][path] != text_hash(ROOT / path):
            errors.append(f"Self-check changed a frozen contract: {path}")
    if integration:
        current_receipts = {str(path): path.read_bytes() for path in (ROOT / "evidence" / role).glob("*.json")}
        if current_receipts != receipt_snapshots:
            errors.append("Integration self-check must not rewrite member receipts; write local outputs only")
    else:
        changes = changed_files()
        for path in changes:
            if not any(fnmatch.fnmatchcase(path, pattern) for pattern in config["owned_paths"]):
                errors.append(f"Self-check changed a file outside role ownership: {path}")
    hashes = {path: text_hash(ROOT / path) for path in config["required_files"]}
    if integration:
        errors.extend(record_errors(role, record, config, ready=True))
        if record.get("status") != "ready_for_review":
            errors.append("Member has not submitted this module for review")
        if (record.get("last_gate") or {}).get("tested_files_sha256") != hashes:
            errors.append("Files differ from the submitted self-check; return to the member")
    if submit:
        errors.extend(record_errors(role, record, config, ready=True))
    if errors:
        return 2, report
    report["status"] = "passed"
    report["tested_files_sha256"] = hashes
    report["verified_revision"] = git("rev-parse", "HEAD")
    report["checked_at"] = datetime.now(timezone.utc).isoformat()
    if submit:
        record["status"] = "ready_for_review"
        record["based_on_commit"] = report["verified_revision"]
        record["changed_files"] = sorted(set(changes) | {config["handoff"]})
        record["last_gate"] = {key: report[key] for key in ("checked_at", "verified_revision", "tested_files_sha256")}
        write_json(ROOT / config["handoff"], record)
        report["handoff_status"] = "ready_for_review"
    return 0, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foundation", action="store_true")
    parser.add_argument("--role", choices=list("ABCD"))
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--integration", action="store_true")
    args = parser.parse_args()
    if args.foundation == bool(args.role) or (args.submit and (args.foundation or args.integration)):
        parser.error("Choose --foundation OR --role; --submit is member-only")
    try:
        manifest = read_json("collaboration/roles.json")
        errors = foundation_errors(manifest)
        if errors:
            code, report = 1, {"status": "failed", "scope": "foundation", "errors": errors}
        elif args.foundation:
            code, report = 0, {"status": "passed", "scope": "shared files and synthetic fixtures only", "workflow_version": "2.0", "contract_version": "1.0", "business_acceptance": "not_evaluated"}
        else:
            code, report = run_role(args.role, manifest, integration=args.integration, submit=args.submit)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, SyntaxError, subprocess.TimeoutExpired) as exc:
        code, report = 1, {"status": "failed", "errors": [str(exc)]}
    if args.role:
        write_json(ROOT / "outputs" / "delivery" / f"{args.role}.json", report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
