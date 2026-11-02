"""Build the final course hand-in from tracked sources and original saved evidence.

Run after the D submission and main rules gate, with a clean main checkout.
No model requests are made. The extracted package is checked using an explicitly
provided interpreter that already has the business dependencies installed.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/final_release_20261102"
PROJECT = "03_完整项目/project/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def build(python):
    assert git("branch", "--show-current") == "main", "Build from reviewed main"
    assert not git("status", "--porcelain"), "Commit the reviewed deliverables first"
    revision = git("rev-parse", "HEAD")
    materials = read(OUT / "materials_check.json")
    assert materials["status"] == "passed"
    assert all(materials[key] == sha((ROOT / path).read_bytes()) for key, path in
               [("pdf_sha256", "docs/report.pdf"), ("pptx_sha256", "docs/presentation.pptx")])
    integration = read(ROOT / "outputs/integration/integration_rules.json")
    assert integration["status"] == "passed"
    assert all(item["status"] == "passed" for item in integration["role_checks"].values())
    ledger = read(ROOT / "ai_usage/C/usage.json")
    records = [r for r in ledger["records"] if r["scope"] == "project_runtime"]
    assert len(records) == 6 and sum(r["calls"] for r in records) == 6
    selected = {}
    forbidden_name = re.compile(r"(?i)(?:^|/)(?:private-access\.json|id_rsa|id_ed25519|.*\.(?:key|pfx|p12|dpapi)|\.env(?:\..*)?)$")
    secret = re.compile(rb"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")

    def validate(name, data):
        assert not forbidden_name.search(name) or name.endswith("/.env.example"), name
        assert not secret.search(data), "Credential-like bytes: " + name
        if name.endswith(".zip"):
            import io
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                assert archive.testzip() is None
                for inner in archive.namelist():
                    if not inner.endswith("/"):
                        validate(name + "/" + inner, archive.read(inner))

    def add(path, name):
        path = Path(path)
        assert path.is_file(), str(path)
        data = path.read_bytes()
        validate(name, data)
        if name in selected:
            assert selected[name] == data, "Conflicting archive path: " + name
        selected[name] = data

    # A full source snapshot, including the unedited historical records.
    tracked = git("ls-files", "-z").split("\0")
    for name in sorted(filter(None, tracked)):
        assert not name.startswith((".git/", ".venv/", "outputs/")), name
        add(ROOT / name, PROJECT + name)
    for part in ("raw", "reference", "dirty", "manifests"):
        for path in (ROOT / "data" / part).iterdir():
            if path.is_file() and path.name != ".gitkeep":
                name = PROJECT + path.relative_to(ROOT).as_posix()
                # Generated manifests, already tracked, must agree byte for byte.
                add(path, name)

    run_bases = [ROOT / "outputs", ROOT / "outputs/smoke_runs", ROOT / "outputs/real_llm_check",
                 ROOT / "outputs/server_reproduction_20261102/downloaded_evidence/data_agent_course/outputs/smoke_runs",
                 ROOT / "outputs/public_gateway_20261102/downloaded_evidence/data_agent_course/outputs"]
    index = []
    run_ids = [(r["source_id"].rsplit(":", 1)[0], "llm") for r in records]
    run_ids += [(materials["rules_run_id"], "rules"), (integration["smoke"]["run_id"], "rules")]
    for run_id, mode in dict(run_ids).items():
        assert re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{8}", run_id)
        matches = [base / run_id for base in run_bases if (base / run_id).is_dir()]
        assert matches, run_id
        folder = matches[0]
        result = read(folder / "run_result.json")
        assert result["run_id"] == run_id and result["status"] == "succeeded" and result["mode"] == mode
        for path in folder.iterdir():
            if path.is_file():
                add(path, PROJECT + "outputs/" + run_id + "/" + path.name)
        index.append({"run_id": run_id, "mode": mode, "original_local_evidence": folder.relative_to(ROOT).as_posix(),
                      "packaged_path": PROJECT + "outputs/" + run_id,
                      "metrics": read(folder / "metrics.json")})

    # Preserve the exact independent-server archives, together with public checks.
    for sub, filename in [("server_reproduction_20261102", "server_evidence_verified_20261102.zip"),
                          ("public_gateway_20261102", "public_gateway_evidence_20261102.zip")]:
        add(ROOT / "outputs" / sub / filename, "04_运行与验收证据/" + filename)
        for filename in ("package_check.json", "public_check.json", "public_media_check.json"):
            path = ROOT / "outputs" / sub / filename
            if path.exists():
                add(path, "04_运行与验收证据/" + sub + "/" + filename)
    for name in ("integration_rules.json", "integration_llm.json", "smoke_rules.json", "smoke_llm.json"):
        path = ROOT / "outputs/integration" / name
        if path.exists():
            add(path, "04_运行与验收证据/local_integration/" + name)
    for name in ("materials_check.json", "report_data.json", "D_submit.log", "main_rules.log"):
        path = OUT / name
        if path.exists():
            add(path, "04_运行与验收证据/materials/" + name)
    for path in (OUT / "ppt_build").glob("validation-*.json"):
        if read(path).get("finalSha256") == materials["pptx_sha256"]:
            add(path, "04_运行与验收证据/materials/ppt_validation.json")
    for path in (ROOT / "outputs/server_reproduction_20261102/downloaded_evidence").rglob("*freeze*.log"):
        # This snapshot is reproducibility evidence, not a replacement of root requirements.
        data = path.read_text(encoding="utf-8-sig").encode("utf-8")
        validate("requirements-server-lock.txt", data)
        selected[PROJECT + "requirements-server-lock.txt"] = data
        break
    for path in (ROOT / "ai_usage").rglob("*"):
        if path.is_file():
            add(path, "05_AI使用记录/" + path.relative_to(ROOT / "ai_usage").as_posix())
    for name in ("summary.json", "summary.md"):
        add(ROOT / "outputs/ai_usage" / name, "05_AI使用记录/" + name)
    for name in ("report.md", "report.pdf"):
        add(ROOT / "docs" / name, "01_项目报告/" + name)
    for relative in ("confusion_matrix_current.png", "public_gateway_20261102/page_service_metrics.jpg"):
        add(ROOT / "docs/report_assets" / relative, "01_项目报告/report_assets/" + relative)
    for name in ("presentation.pptx", "presentation_guide.md", "presentation_outline.md", "demo_script.md", "contributions.md", "acceptance.md"):
        add(ROOT / "docs" / name, "02_课堂演示/" + name)
    guide = (ROOT / "docs/presentation_guide.md").read_bytes()
    selected["02_课堂演示/PPT制作与课堂展示指南.md"] = guide

    bundle = OUT / "source.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle), "main"], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(["git", "bundle", "verify", str(bundle)], cwd=ROOT, check=True, capture_output=True)
    add(bundle, "03_完整项目/source.bundle")
    selected["04_运行与验收证据/运行索引.json"] = json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8")
    selected["交付说明.md"] = f"""# 数据自动清洗与分类智能体：课程交付包

源代码与材料提交：{revision}。原服务器业务验证提交：d5d5787cfb5d641e2eb70fdedbe5950501272163。

| 目录 | 主要内容 |
| --- | --- |
| 01_项目报告 | 6页报告PDF、Markdown与对应实际图片 |
| 02_课堂演示 | 7页可编辑PPT、讲者备注、PPT制作与课堂展示指南、贡献和验收清单 |
| 03_完整项目 | 完整源码与正式数据、6次实际LLM运行及规则对照；source.bundle保留main完整Git历史 |
| 04_运行与验收证据 | 异机/公网原始证据包、实际运行索引、本次材料与集成检查 |
| 05_AI使用记录 | 四人实际记录、提示词及汇总；不可核实用量/费用保留null |

主LLM运行：{materials['primary_run_id']}，median/most_frequent，训练6,998/测试3,000，Accuracy85.23%、Macro-F1 0.787282，矩阵[[2108,182],[261,449]]。
规则对照：{materials['rules_run_id']}，median/Unknown，训练7,000/测试3,000，Accuracy85.23%、Macro-F1 0.788846。
原始run_result和events保留服务器当时的绝对路径，未改写证据；网页历史加载支持将完整运行目录搬迁后回放。

## 安装与复现

使用Python3.12（服务器实测3.12.10）。进入03_完整项目/project，创建.venv，激活后执行：

```powershell
python -m pip install -r requirements.txt
python -m src.cli --mode rules
python -m streamlit run app.py
```

包已包含正式数据；如需重建，先备份现有数据，再执行`python scripts/prepare_data.py --seed 42 --sample-size 10000`。
模型模式在本地安全设置LLM_API_URL、LLM_API_KEY、LLM_MODEL后执行`python -m src.cli --mode llm`；URL为https://api.deepseek.com，模型deepseek-flash，.env不自动加载。包内没有API key或演示登录口令。

若需含Git上下文的完整门禁，在03_完整项目下执行：

```powershell
git clone -b main source.bundle reproduced
```

将project/data和project/outputs复制到reproduced同名目录；在reproduced建立环境后执行`python scripts/check_integration.py --mode rules`。模型配置完成后可执行`--mode llm`，该步骤会产生新的实际请求及AI运行记录。

## 课堂展示

公网入口：https://111.230.149.166/。演示账号demo，口令由展示者私下保管。先读02_课堂演示/PPT制作与课堂展示指南.md，按7分钟建议安排讲述，第6页切换网页。
预检、重绘、历史回放不请求模型；只有点击开始处理才新建运行。已保存的主LLM和规则对照分别说明原始模式与run_id，新的模型选择及指标以实际输出为准。

## 验证范围

独立服务器安装、正式数据重建、rules/真实LLM集成、网页导出、服务重启及关闭SSH后的14项公网检查已有证据。
本次材料制作没有新增模型请求。6次项目请求累计输入5,928/输出5,652 token，费用未知；开发内部用量不计为零。
课前仍需检查教室网络/投影、原生PowerPoint打开、计时排练及录屏。整机重启与手机实机未测试。包的解压/哈希及本机规则运行检查不替代异机或课堂验收。
历史文档是对应时间快照；当前正式报告、指南及acceptance.md使用最新口径。

清单.json记录每个交付文件的SHA-256；SHA256SUMS.txt可独立核对。本次包检验结果保存于包外同目录package_check.json，避免自引用校验和。
""".encode("utf-8")
    manifest = {"revision": revision, "created_at": datetime.now(timezone.utc).isoformat(),
                "primary_run_id": materials["primary_run_id"], "runtime_requests": 6,
                "input_tokens": 5928, "output_tokens": 5652, "cost": None,
                "files": [{"path": name, "bytes": len(data), "sha256": sha(data)} for name, data in sorted(selected.items())]}
    selected["清单.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    selected["SHA256SUMS.txt"] = "\n".join(f"{sha(data)}  {name}" for name, data in sorted(selected.items())).encode("utf-8") + b"\n"
    target = OUT / "data_agent_course_final_20261102.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in selected.items():
            archive.writestr(name, data)
    digest = sha(target.read_bytes())
    extracted = OUT / ("unpacked_" + digest[:12])
    extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert all((extracted / name).resolve().is_relative_to(extracted.resolve()) for name in archive.namelist())
        archive.extractall(extracted)
    assert all(sha((extracted / item["path"]).read_bytes()) == item["sha256"] for item in manifest["files"])
    clone = extracted / "03_完整项目/reproduced"
    process = subprocess.run(["git", "clone", "-b", "main", str(extracted / "03_完整项目/source.bundle"), str(clone)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert process.returncode == 0, process.stderr
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clone).decode().strip() == revision
    for part in ("data", "outputs"):
        shutil.copytree(extracted / PROJECT / part, clone / part, dirs_exist_ok=True)
    process = subprocess.run([str(python), "-m", "src.cli", "--mode", "rules"], cwd=clone,
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    (OUT / "package_rules.log").write_text(process.stdout + process.stderr, encoding="utf-8")
    assert process.returncode == 0, "Extracted bundle rules CLI failed; see package_rules.log"
    result = json.loads(process.stdout)
    assert result["status"] == "succeeded" and result["mode"] == "rules"
    metrics = read(Path(result["output_dir"]) / "metrics.json" if Path(result["output_dir"]).is_absolute() else clone / result["output_dir"] / "metrics.json")
    assert metrics["test_rows"] == 3000 and abs(metrics["accuracy"] - .8523333333333334) < 1e-12
    assert abs(metrics["macro_f1"] - .788845681782975) < 1e-12
    receipt = {"status": "passed", "checked_at": datetime.now(timezone.utc).isoformat(),
               "revision": revision, "zip": str(target), "file_count": len(selected),
               "bytes": target.stat().st_size, "sha256": digest, "crc_and_all_file_hashes": "passed",
               "credential_pattern_and_forbidden_file_scan": "passed", "git_bundle_clone_head_matches": True,
               "same_machine_rules_roundtrip": {"exit_code": process.returncode, "run_id": result["run_id"], "metrics": metrics},
               "scope": "Same-machine archive/bundle restoration and actual rules CLI using existing dependencies; independent server evidence is separately preserved.",
               "new_model_requests": 0, "not_run": ["native_powerpoint", "classroom_network", "timed_rehearsal_recording", "whole_server_reboot", "phone_hardware"]}
    (OUT / "package_check.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True, help="Interpreter with installed business dependencies")
    build(parser.parse_args().python.resolve())
