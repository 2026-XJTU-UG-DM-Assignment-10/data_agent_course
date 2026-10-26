"""Build one self-contained Markdown context packet per role, without secrets or raw logs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=["A", "B", "C", "D", "all"], default="all")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "collaboration/roles.json").read_text(encoding="utf-8"))
    repository_url = manifest["repository_url"].rstrip("/")
    output = ROOT / "outputs" / "ai_briefs"
    output.mkdir(parents=True, exist_ok=True)
    roles = "ABCD" if args.role == "all" else args.role
    common = [
        "AGENTS.md", "README.md", "docs/START_HERE.md",
        "docs/低沟通协作协议.md", "docs/公共接口说明.md", "docs/AI使用记录规范.md",
        "src/schema.py", "src/contracts.py", "collaboration/contract_hashes.json",
        "checks/README.md", "evidence/README.md", "examples/README.md",
        "docs/数据处理智能体_AI开发任务书.md", "docs/integration_log.md",
    ]
    for role in roles:
        config = manifest["roles"][role]
        usage = json.loads((ROOT / config["ai_usage_log"]).read_text(encoding="utf-8"))
        content = [
            f"# 成员 {role} 的 AI 开工资料（自包含快照）\n",
            f"生成时间：{datetime.now(timezone.utc).isoformat()}；协作协议 2.0；业务契约 1.0。\n",
            f"你负责成员 {role}，分支为 `{config['branch']}`。请按下面的角色指令、公共契约和交付规则实现本人范围。\n",
            "本文件用于给任何 AI 一次提供所需上下文；不包含 Git 元数据、业务完成结果、API 密钥或原始运行日志。\n",
            "有仓库访问能力时，以仓库当前状态和本人交接为准；只有本文件时，将它作为开工快照，输出文件内容和待执行命令，不声称已在真实仓库运行。应用修改、提交和复验仍在成员已克隆的仓库中进行。\n",
            "后续交接时可重新生成此文件；不要用旧快照覆盖已接受的工作。\n",
            "## 本人的机器可读角色清单\n\n```json\n" + json.dumps({"workflow_version": "2.0", "contract_version": "1.0", "role": role, **config}, ensure_ascii=False, indent=2) + "\n```\n",
        ]
        sources = [config["prompt"], *common, config["task"], config["handoff"], f"docs/handoff_{role}.md", config["ai_usage_log"], *config["offline_inputs"]]
        sources.extend(reference for record in usage["records"] for reference in record["prompt_files"])
        included = set()
        for relative in sources:
            if relative in included:
                continue
            included.add(relative)
            path = (ROOT / relative).resolve()
            allowed = relative in {"AGENTS.md", "README.md"} or relative.startswith(("docs/", "src/", "prompts/", "handoffs/", "examples/", "collaboration/", "checks/", "evidence/", "ai_usage/"))
            if not allowed or not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError(f"Unsafe or missing public context file: {relative}")
            text = path.read_text(encoding="utf-8")
            if relative == "docs/数据处理智能体_AI开发任务书.md":
                # Keep the scope, data and formal deliverables; avoid duplicating
                # implementation/workflow details already included in full.
                selected, keep = [], False
                for line in text.splitlines():
                    if line.startswith("## "):
                        number = line[3:].split(".", 1)[0]
                        keep = number in {"2", "3", "10"}
                    if keep:
                        selected.append(line)
                text = "本文节选第 2、3、10 节；公共接口、协作协议及本角色要求已在本资料中全文提供。\n\n" + "\n".join(selected)
            content.append(f"\n---\n\n## 源文件：{relative}\n")
            if path.suffix == ".md":
                def link_to_repository(match):
                    target = match.group(1)
                    if target.startswith(("http:", "https:", "#", "mailto:")):
                        return match.group(0)
                    filename, separator, anchor = target.partition("#")
                    destination = (path.parent / filename).resolve()
                    if not destination.is_relative_to(ROOT) or not destination.exists():
                        raise ValueError(f"Broken source link in {relative}: {target}")
                    url = repository_url + "/blob/main/" + quote(destination.relative_to(ROOT).as_posix(), safe="/")
                    if separator:
                        url += "#" + anchor
                    return "](" + url + ")"
                text = re.sub(r"\]\(([^)]+)\)", link_to_repository, text)
                content.append(text + "\n")
            else:
                language = {".py": "python", ".json": "json", ".csv": "csv", ".svg": "xml"}.get(path.suffix, "text")
                content.append(f"\n```{language}\n{text.rstrip()}\n```\n")
        target = output / f"member_{role}_AI_brief.md"
        target.write_text("\n".join(content), encoding="utf-8")
        print(f"Created outputs/ai_briefs/{target.name}")


if __name__ == "__main__":
    main()
