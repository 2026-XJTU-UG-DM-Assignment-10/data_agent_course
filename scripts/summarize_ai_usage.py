"""Validate per-member AI usage and summarize known values without inventing totals."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{20,})\b")


def load_records(root: Path, roles: str = "ABCD", *, require_records: bool = False) -> list[dict]:
    """Return validated records. Unknown usage is null, never an inferred zero."""
    records, identifiers, sources = [], set(), set()
    for role in roles:
        path = root / "ai_usage" / role / "usage.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("schema_version") != "1.0" or document.get("role") != role:
            raise ValueError(f"Invalid AI usage header: {path}")
        if not isinstance(document.get("coverage_note"), str) or not document["coverage_note"].strip():
            raise ValueError(f"Describe log coverage: {path}")
        items = document.get("records")
        if not isinstance(items, list) or (require_records and not items):
            raise ValueError(f"Role {role}: actual AI usage records required before delivery")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Role {role}: records must be objects")
            for field in ("id", "time", "tool", "parameters_note", "source_id", "notes"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError(f"Role {role}: nonempty {field} required")
            identifier = item["id"]
            if not identifier.startswith(role + "-") or identifier in identifiers:
                raise ValueError(f"Duplicate or wrong-role AI record ID: {identifier}")
            identifiers.add(identifier)
            moment = datetime.fromisoformat(item["time"])
            if moment.tzinfo is None:
                raise ValueError(f"Timestamp needs timezone: {identifier}")
            if item.get("scope") not in {"development", "project_runtime"}:
                raise ValueError(f"Invalid scope: {identifier}")
            if item["scope"] == "project_runtime" and role != "C":
                raise ValueError("Only C registers project runtime requests, including requests launched by D")
            source = (item["scope"], item["source_id"])
            if source in sources:
                raise ValueError(f"Repeated source/session/request: {source}")
            sources.add(source)
            if "model" not in item or (item["model"] is not None and (not isinstance(item["model"], str) or not item["model"].strip())):
                raise ValueError(f"Model must be the actual displayed ID/name or null: {identifier}")
            if not isinstance(item.get("parameters"), dict):
                raise ValueError(f"Parameters must be an object: {identifier}")
            for field in ("calls", "interactions", "input_tokens", "output_tokens"):
                value = item.get(field)
                if field not in item or (value is not None and (type(value) is not int or value < 0)):
                    raise ValueError(f"{identifier}: {field} must be a nonnegative integer or null")
            if item["scope"] == "project_runtime" and item["calls"] != 1:
                raise ValueError(f"Runtime: one record per actual request attempt, calls=1: {identifier}")
            if item.get("result") not in {"succeeded", "failed", "partial"}:
                raise ValueError(f"Declare the actual outcome: {identifier}")
            cost = item.get("cost")
            if not isinstance(cost, dict) or cost.get("kind") not in {"actual", "estimate", "unknown"}:
                raise ValueError(f"Invalid cost object: {identifier}")
            if not isinstance(cost.get("basis"), str) or not cost["basis"].strip():
                raise ValueError(f"Cost needs a source or unknown reason: {identifier}")
            amount = cost.get("amount")
            if cost["kind"] == "unknown":
                if "amount" not in cost or amount is not None:
                    raise ValueError(f"Unknown cost must have amount=null: {identifier}")
            elif type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0:
                raise ValueError(f"Known cost must be finite and nonnegative: {identifier}")
            elif not isinstance(cost.get("currency"), str) or not re.fullmatch(r"[A-Z]{3}", cost["currency"]):
                raise ValueError(f"Known cost needs a currency such as CNY/USD: {identifier}")
            prompts = item.get("prompt_files")
            if not isinstance(prompts, list) or not prompts:
                raise ValueError(f"Prompt transcript files required: {identifier}")
            content = json.dumps(item, ensure_ascii=False)
            for reference in prompts:
                if not isinstance(reference, str) or not reference.startswith(f"ai_usage/{role}/prompts/"):
                    raise ValueError(f"Prompt must be in this member's prompt directory: {identifier}")
                prompt = (root / reference).resolve()
                if not prompt.is_relative_to((root / "ai_usage" / role / "prompts").resolve()) or prompt.suffix != ".md":
                    raise ValueError(f"Unsafe prompt path: {reference}")
                text = prompt.read_text(encoding="utf-8")
                if not text.strip():
                    raise ValueError(f"Empty prompt transcript: {reference}")
                content += text
            if SECRET.search(content):
                raise ValueError(f"Possible credential in public AI usage/prompt: {identifier}")
            records.append({**item, "role": role})
    return records


def summarize(records: list[dict]) -> dict:
    groups = defaultdict(list)
    for item in records:
        groups[(item["scope"], item["role"], item["model"])].append(item)
    rows = []
    for (scope, role, model), items in sorted(groups.items(), key=lambda pair: str(pair[0])):
        row = {"scope": scope, "role": role, "model": model, "records": len(items)}
        for field in ("calls", "interactions", "input_tokens", "output_tokens"):
            row[f"known_{field}"] = sum(item[field] for item in items if item[field] is not None)
            row[f"known_{field}_records"] = sum(item[field] is not None for item in items)
            row[f"unknown_{field}_records"] = sum(item[field] is None for item in items)
        rows.append(row)
    costs = defaultdict(Decimal)
    unknown = defaultdict(int)
    for item in records:
        cost = item["cost"]
        if cost["kind"] == "unknown":
            unknown[item["scope"]] += 1
        else:
            costs[(item["scope"], cost["kind"], cost["currency"])] += Decimal(str(cost["amount"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope_note": "Known subtotals only; unknowns remain unknown. Development does not prove a runtime LLM run.",
        "rows": rows,
        "cost_subtotals": [{"scope": scope, "kind": kind, "currency": currency, "amount": str(amount)}
                           for (scope, kind, currency), amount in sorted(costs.items())],
        "unknown_cost_records": dict(unknown),
        "roles_without_records": [role for role in "ABCD" if not any(item["role"] == role for item in records)],
    }


def render_markdown(summary: dict) -> str:
    lines = ["# AI 使用记录汇总", "", f"生成时间：{summary['generated_at']}", "",
             "以下只统计已登记记录，已知小计不代表完整总量；未知项未按 0 处理。开发辅助记录不能替代真实项目运行证据。", "",
             "| 范围 | 成员 | 模型 | 记录数 | 已知模型请求数 | 请求数未知的记录 | 已知对话轮次 |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in summary["rows"]:
        model = (row["model"] or "未知").replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        scope = "开发辅助" if row["scope"] == "development" else "项目运行"
        calls = row["known_calls"] if row["known_calls_records"] else "未知"
        interactions = row["known_interactions"] if row["known_interactions_records"] else "未知"
        lines.append(f"| {scope} | {row['role']} | {model} | {row['records']} | {calls} | {row['unknown_calls_records']} | {interactions} |")
    if not summary["rows"]:
        lines.append("| 尚无实际记录 | — | — | 0 | — | — | — |")
    lines += ["", "对话轮次与模型请求数分开统计；逐项参数、提示词、token 及未知项详见各成员原日志和 summary.json。", "",
              "## 费用", "", "实际支出与估算分开，各币种分别列示，均为已知小计。", ""]
    for item in summary["cost_subtotals"]:
        scope = "开发辅助" if item["scope"] == "development" else "项目运行"
        kind = "实际支出" if item["kind"] == "actual" else "估算"
        lines.append(f"- {scope}／{kind}：{item['amount']} {item['currency']}")
    if not summary["cost_subtotals"]:
        lines.append("- 尚无可核实的费用数值。")
    for scope, count in sorted(summary["unknown_cost_records"].items()):
        lines.append(f"- {'开发辅助' if scope == 'development' else '项目运行'}：{count} 条记录费用未知。")
    lines += ["", "未登记任何记录的成员：" + ("、".join(summary["roles_without_records"]) or "无") + "。", "",
              "记录覆盖范围见 ai_usage/X/usage.json 中的 coverage_note；未记录的历史会话不能推断为未使用 AI。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=list("ABCD"))
    parser.add_argument("--check", action="store_true", help="Validate only; do not generate a report")
    parser.add_argument("--require-records", action="store_true")
    args = parser.parse_args()
    try:
        records = load_records(ROOT, args.role or "ABCD", require_records=args.require_records)
        if args.check:
            print(json.dumps({"status": "passed", "records": len(records), "scope": "usage log structure, not billing verification"}))
        else:
            summary = summarize(records)
            output = ROOT / "outputs" / "ai_usage"
            output.mkdir(parents=True, exist_ok=True)
            (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (output / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
            print("Created outputs/ai_usage/summary.json and summary.md; unknowns were not filled in.")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
