"""Archive actual LLM verification alongside the preserved rules-stage materials."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/real_llm_check"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build():
    integration = json.loads((ROOT / "outputs/integration/integration_llm.json").read_text(encoding="utf-8"))
    assert integration["status"] == "passed"
    assert integration["smoke"]["real_llm_checked"] and integration["smoke"]["formal_data_checked"]
    assert all(item["status"] == "passed" for item in integration["role_checks"].values())
    ledger = json.loads((ROOT / "ai_usage/C/usage.json").read_text(encoding="utf-8"))
    records = [item for item in ledger["records"] if item["scope"] == "project_runtime"]
    assert len(records) == 3 and len({item["source_id"] for item in records}) == 3
    assert all(item["calls"] == 1 and item["result"] == "succeeded" for item in records)
    selected = {}

    def add(source, name):
        source = Path(source)
        assert source.is_file(), str(source)
        assert source.name == ".env.example" or not source.name.startswith(".env")
        assert source.suffix not in (".pyc", ".pyo")
        data = source.read_bytes()
        if source.suffix.lower() in (".md", ".py", ".json", ".jsonl", ".txt", ".mjs", ".example", ".log"):
            assert not re.search(rb"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b", data), "Possible credential: " + str(source)
        selected[name] = data

    names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    for name in sorted(set(names) - {""}):
        if not name.startswith((".git/", ".venv/", "outputs/")):
            add(ROOT / name, "project/" + name)
    for part in ("raw", "reference", "dirty", "manifests"):
        for path in (ROOT / "data" / part).iterdir():
            if path.is_file() and path.name != ".gitkeep":
                add(path, "project/" + path.relative_to(ROOT).as_posix())
    run_folders = [ROOT / "outputs/20261030T070819Z-7779c942"]
    for item in records:
        run_id = item["source_id"].rsplit(":", 1)[0]
        assert re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{8}", run_id)
        matches = [base / run_id for base in (OUT, ROOT / "outputs/smoke_runs") if (base / run_id).is_dir()]
        assert len(matches) == 1
        folder = matches[0]
        result = json.loads((folder / "run_result.json").read_text(encoding="utf-8"))
        assert result["run_id"] == run_id and result["mode"] == "llm" and result["status"] == "succeeded"
        run_folders.append(folder)
    for folder in run_folders:
        for path in folder.iterdir():
            if path.is_file():
                add(path, "project/" + path.relative_to(ROOT).as_posix())
    for name in ("integration_llm.json", "smoke_llm.json", "integration_rules.json"):
        add(ROOT / "outputs/integration" / name, "本轮验证/" + name)
    for name in ("deepseek_C_20261102.json", "deepseek_C_20261102.log",
                 "deepseek_main_initial_failure_20261102.json", "deepseek_smoke_initial_failure_20261102.json",
                 "deepseek_main_verified_20261102.log", "C_real_delivery_20261102.log",
                 "C_main_llm_delivery_20261102.log", "D_llm_fix_delivery_20261102.log"):
        add(OUT / name, "本轮验证/" + name)
    for name in ("summary.json", "summary.md"):
        add(ROOT / "outputs/ai_usage" / name, "AI使用记录/" + name)
    manifest = {
        "scope": "rules and real LLM technical verification; human acceptance pending",
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "verified_code_revision": integration["role_checks"]["D"]["verified_revision"],
        "real_model_run_id": integration["smoke"]["run_id"],
        "runtime_requests": len(records),
        "input_tokens": sum(item["input_tokens"] for item in records),
        "output_tokens": sum(item["output_tokens"] for item in records),
        "cost": None,
        "materials": "Existing PDF/PPT are rules-stage snapshots; real LLM supplement is docs/report_llm_validation_20261102.md",
        "not_run": ["human_cross_machine", "human_rehearsal", "native_powerpoint", "manual_llm_ui_and_recording", "real_service_correction"],
        "files": [{"path": name, "bytes": len(data), "sha256": sha(data)} for name, data in sorted(selected.items())],
    }
    selected["交付清单.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    selected["请先阅读.txt"] = ("真实LLM技术验证已通过，真人验收仍待。进入project，阅读README及docs/report_llm_validation_20261102.md。\n"
                                  "本包包含正式数据、旧规则主运行、三次真实模型运行、初次门禁误报及修复后通过证据、源码和AI账本。\n"
                                  "PDF/PPT保持规则阶段快照；业务prompt属于真实项目请求，未新增配置指导对话的开发prompt记录。\n"
                                  "不包含密钥。新终端仍需本地设置LLM_API_URL、LLM_API_KEY、LLM_MODEL；.env不自动加载。\n").encode("utf-8")
    target = OUT / "data_agent_course_llm_verified_20261102.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in selected.items():
            archive.writestr(name, data)
    package_sha = sha(target.read_bytes())
    extract = OUT / ("unpacked_llm_verified_" + package_sha[:10])
    extract.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert all((extract / name).resolve().is_relative_to(extract.resolve()) for name in archive.namelist())
        archive.extractall(extract)
    assert all(sha((extract / item["path"]).read_bytes()) == item["sha256"] for item in manifest["files"])
    report = {"status": "passed", "scope": manifest["scope"], "revision": manifest["revision"],
              "file_count": len(selected), "bytes": target.stat().st_size, "zip_sha256": package_sha,
              "all_extracted_hashes_match": True, "real_model_run_id": manifest["real_model_run_id"],
              "runtime_requests": len(records), "not_run": manifest["not_run"]}
    (OUT / "llm_package_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    build()
