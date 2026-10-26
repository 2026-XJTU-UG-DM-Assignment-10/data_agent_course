"""D's read-only integration runner. It never merges, switches, or pushes branches."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["rules", "llm"], default="rules")
    args = parser.parse_args()
    report = {"mode": args.mode, "status": "not_ready", "role_checks": {}, "errors": []}
    output = ROOT / "outputs" / "integration"
    output.mkdir(parents=True, exist_ok=True)
    for role in "ABCD":
        process = subprocess.run([sys.executable, "scripts/check_delivery.py", "--role", role, "--integration"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        try:
            result = json.loads(process.stdout)
        except json.JSONDecodeError:
            result = {"status": "failed", "errors": [process.stderr[-3000:] or process.stdout[-3000:]]}
        report["role_checks"][role] = result
        if process.returncode:
            report["errors"].append(f"Role {role} is not ready; see its check result")
    if not report["errors"]:
        smoke = ROOT / "scripts" / "smoke_check.py"
        smoke_report = output / f"smoke_{args.mode}.json"
        if smoke_report.exists():
            # Prevent a stale success report from satisfying this run.
            previous_bytes = smoke_report.read_bytes()
            previous_mtime = smoke_report.stat().st_mtime_ns
        else:
            previous_bytes = None
            previous_mtime = None
        if not smoke.exists():
            report["errors"].append("D has not implemented scripts/smoke_check.py")
        else:
            process = subprocess.run([sys.executable, str(smoke), "--mode", args.mode, "--report", str(smoke_report)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if process.returncode or not smoke_report.exists():
                report["errors"].append("Real-module smoke check failed or did not create its report")
                report["smoke_output"] = process.stdout[-3000:] + process.stderr[-3000:]
            else:
                current = smoke_report.read_bytes()
                if previous_mtime == smoke_report.stat().st_mtime_ns and current == previous_bytes:
                    report["errors"].append("Smoke report was not regenerated")
                smoke_result = json.loads(current)
                report["smoke"] = smoke_result
                required = {"status": "passed", "mode": args.mode, "uses_real_modules": True, "formal_data_checked": True}
                if args.mode == "llm":
                    required["real_llm_checked"] = True
                if any(smoke_result.get(key) != value for key, value in required.items()):
                    report["errors"].append("Smoke report does not prove the requested scope")
                evidence = smoke_result.get("evidence", [])
                if not isinstance(evidence, list) or not evidence:
                    report["errors"].append("Smoke report needs real evidence paths")
                    evidence = []
                for name in evidence:
                    if not isinstance(name, str):
                        report["errors"].append("Smoke evidence path must be a string")
                        continue
                    path = (ROOT / name).resolve()
                    if Path(name).is_absolute() or not path.is_relative_to(ROOT) or not path.exists() or not name.replace("\\", "/").startswith(("outputs/", "data/manifests/")):
                        report["errors"].append("Smoke evidence path is invalid")
    if not report["errors"]:
        report["status"] = "passed"
    (output / f"integration_{args.mode}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=True))
        raise SystemExit(1)
