"""Regression checks for delivery control, using only an isolated temporary repo.

The temporary business modules are explicit test doubles of workflow inputs.
This does not implement or validate any course business module or real LLM call.
"""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cleanup_temporary_repo(temp_root: Path, qa_root: Path) -> None:
    temp_root, qa_root = temp_root.resolve(), qa_root.resolve()
    if temp_root.parent != qa_root or not temp_root.is_relative_to(ROOT):
        raise RuntimeError("Refusing cleanup outside the verified QA directory")
    def remove_read_only(function, name, error_info):
        path = Path(name).resolve()
        if not path.is_relative_to(temp_root) or not isinstance(error_info[1], PermissionError):
            raise error_info[1]
        path.chmod(stat.S_IREAD | stat.S_IWRITE)
        function(name)
    shutil.rmtree(temp_root, onerror=remove_read_only)


def main() -> None:
    qa_root = (ROOT / "outputs" / "workflow_qa").resolve()
    qa_root.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="control-test-", dir=qa_root)).resolve()
    if temp_root.parent != qa_root or not temp_root.is_relative_to(ROOT):
        raise RuntimeError("Unexpected temporary directory")
    project = temp_root / "project"
    project.mkdir()
    passed = []
    try:
        names = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT).decode("utf-8").split("\0")
        for name in set(names) - {""}:
            source = ROOT / name
            if source.is_file():
                target = project / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

        def command(*args: str) -> str:
            result = subprocess.run(args, cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if result.returncode:
                raise AssertionError(result.stderr or result.stdout)
            return result.stdout

        def gate(expected: int, *args: str) -> dict:
            result = subprocess.run([sys.executable, "-B", "scripts/check_delivery.py", *args], cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if result.returncode != expected:
                raise AssertionError(f"Expected {expected}, got {result.returncode}: {result.stdout} {result.stderr}")
            return json.loads(result.stdout)

        command("git", "init", "-b", "main")
        command("git", "config", "user.name", "Workflow Control Test")
        command("git", "config", "user.email", "workflow-test@example.invalid")
        command("git", "add", ".")
        command("git", "-c", "commit.gpgsign=false", "commit", "-m", "temporary workflow test baseline")
        command("git", "update-ref", "refs/remotes/origin/main", "HEAD")
        assert gate(0, "--foundation")["business_acceptance"] == "not_evaluated"
        passed.append("foundation_does_not_claim_business_completion")
        command("git", "switch", "-c", "member-b-clean")
        assert gate(2, "--role", "B", "--submit")["status"] == "not_ready"
        passed.append("missing_business_is_not_ready")

        normalizer = project / "src/normalization.py"
        cleaner = project / "src/cleaner.py"
        normalizer.write_text("def normalize_frame(df):\n    return df, None\n", encoding="utf-8")
        cleaner_text = "def clean_training_data(train_df, plan):\n    return train_df, None, None\n\ndef transform_test_data(test_df, cleaning_state):\n    return test_df, None\n"
        cleaner.write_text(cleaner_text, encoding="utf-8")
        (project / "docs/cleaning.md").write_text("Workflow control simulation only.\n", encoding="utf-8")
        self_check = '''import json, sys
from datetime import datetime, timezone
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.normalization import normalize_frame
assert normalize_frame([1])[0] == [1]
out = root / 'outputs/member_B'
out.mkdir(parents=True, exist_ok=True)
(out/'control.json').write_text(json.dumps({'scope':'workflow-control-test-only'}), encoding='utf-8')
if '--integration' not in sys.argv:
    receipt = {'workflow_version':'2.0','contract_version':'1.0','role':'B','scope':'fixtures','status':'passed','checked_at':datetime.now(timezone.utc).isoformat(),'command':'python checks/check_B.py','uses_test_doubles':True,'summary':{'scope':'temporary workflow control test only'},'artifacts':['outputs/member_B/control.json']}
    (root/'evidence/B/fixtures.json').write_text(json.dumps(receipt), encoding='utf-8')
print(json.dumps({'workflow_control_only':True,'integration':'--integration' in sys.argv}))
'''
        (project / "checks/check_B.py").write_text(self_check, encoding="utf-8")
        handoff_path = project / "handoffs/B.json"
        record = json.loads(handoff_path.read_text(encoding="utf-8"))
        record["status"] = "working"
        record["completed"] = ["Temporary workflow control simulation only"]
        record["verification"]["fixtures"] = {"status": "passed", "evidence": ["evidence/B/fixtures.json"]}
        handoff_path.write_text(json.dumps(record), encoding="utf-8")

        readme = project / "README.md"
        original = readme.read_bytes()
        readme.write_bytes(original + b"\nControl-test out-of-scope change.\n")
        assert any("outside role" in error for error in gate(2, "--role", "B", "--submit")["errors"])
        readme.write_bytes(original)
        passed.append("cross_role_edits_rejected")

        frozen = project / "src/schema.py"
        original = frozen.read_bytes()
        frozen.write_bytes(original + b"\n# controlled contract drift\n")
        assert gate(1, "--role", "B", "--submit")["status"] == "failed"
        frozen.write_bytes(original)
        passed.append("frozen_contract_drift_rejected")

        cleaner.write_text(cleaner_text.replace("train_df, plan)", "train_df, plan=None)"), encoding="utf-8")
        assert any("required" in error for error in gate(2, "--role", "B", "--submit")["errors"])
        cleaner.write_text(cleaner_text, encoding="utf-8")
        passed.append("signature_default_drift_rejected")

        result = gate(0, "--role", "B", "--submit")
        assert result["handoff_status"] == "ready_for_review"
        submitted = json.loads(handoff_path.read_text(encoding="utf-8"))
        assert "evidence/B/fixtures.json" in submitted["changed_files"]
        passed.append("verified_submission_records_receipt_and_state")

        command("git", "add", ".")
        command("git", "-c", "commit.gpgsign=false", "commit", "-m", "temporary role control input")
        command("git", "switch", "main")
        command("git", "merge", "--ff-only", "member-b-clean")
        result = gate(0, "--role", "B", "--integration")
        assert "--integration" in result["self_check"]["command"]
        assert json.loads(result["self_check"]["stdout_tail"])["integration"] is True
        passed.append("integration_rechecks_with_real_dependency_flag")

        cleaner.write_text(cleaner_text + "\n# controlled post-submission change\n", encoding="utf-8")
        assert any("Files differ" in error for error in gate(2, "--role", "B", "--integration")["errors"])
        cleaner.write_text(cleaner_text, encoding="utf-8")
        passed.append("post_submission_source_drift_rejected")

        receipt_path = project / "evidence/B/fixtures.json"
        original_receipt = receipt_path.read_bytes()
        receipt = json.loads(original_receipt)
        receipt["api_key"] = "not-a-real-secret; controlled negative test"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        assert any("Sensitive" in error for error in gate(2, "--role", "B", "--integration")["errors"])
        receipt_path.write_bytes(original_receipt)
        passed.append("raw_or_sensitive_receipt_fields_rejected")

        record = json.loads(handoff_path.read_text(encoding="utf-8"))
        record["verification"]["fixtures"] = "passed"
        handoff_path.write_text(json.dumps(record), encoding="utf-8")
        result = gate(1, "--foundation")
        assert any("must be an object" in error for error in result["errors"])
        passed.append("malformed_handoff_reported_without_traceback")

        report = {"status": "passed", "scope": "workflow control only; temporary business inputs are test doubles", "cases": passed}
    finally:
        # Verify the exact absolute target before the recursive temporary cleanup.
        cleanup_temporary_repo(temp_root, qa_root)
    (qa_root / "latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
