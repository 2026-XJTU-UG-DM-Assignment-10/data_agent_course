# AI 使用记录与汇总规范

这是协作协议 2.0 的补充，业务接口仍为 1.0。四人分别记录开发时的 AI 使用，最后合并统计；项目实际运行时的模型请求单独记账。无需每天集中填报。

## 谁记录、放在哪里

| 成员 | 本人账本 | 本人提示词文件 | 负责范围 |
| --- | --- | --- | --- |
| A | `ai_usage/A/usage.json` | `ai_usage/A/prompts/` | 本人开发与材料制作 |
| B | `ai_usage/B/usage.json` | `ai_usage/B/prompts/` | 本人开发与材料制作 |
| C | `ai_usage/C/usage.json` | `ai_usage/C/prompts/` | 本人开发；统一登记项目运行请求 |
| D | `ai_usage/D/usage.json` | `ai_usage/D/prompts/` | 本人开发与集成；最终汇总 |

每人只修改自己的目录，账本和脱敏提示词随个人分支提交。D 合并分支后运行汇总，不手工复制其他人的条目。原始项目运行日志仍由 C 的 pipeline 自动写到 `outputs/<run_id>/events.jsonl`；这份账本不取代原始日志。

## 何时记录

1. 开始使用 AI 时，创建一条本人开发会话记录，保存本轮实际输入；开工指令和任务文件可以注明仓库路径与使用时的提交版本。
2. 同一模型的同一段开发会话继续更新原条目，追加追问与修正提示词，不把同一会话另抄一份。换模型或另开会话时新建条目。AI 能编辑文件时负责更新，不能编辑时输出 JSON 条目和提示词文件内容，由成员保存。
3. 结束一次工作、换 AI 或交接前，成员核对模型名称、参数、次数、费用及提示词是否符合实际；无需逐个工具调用手填表。
4. C 对每次真实项目请求登记一条 `project_runtime` 记录，成功、失败和修正请求均包含。D 点击页面触发的请求也只由 C 登记；使用 `run_id:请求序号` 作为唯一 `source_id`，引用实际日志。
5. 规则模式、模拟客户端和离线自测不是模型请求，不登记为真实项目调用。当前空账本只是尚未记录，不能据此声称没有使用 AI。

## 一条记录的内容

以下只是结构示例，不能复制后当成真实调用证据；实际账本初始为空。字段名固定，实际记录替换示例内容。

```json
{
  "id": "B-20261027-01",
  "scope": "development",
  "time": "2026-10-27T14:00:00+08:00",
  "tool": "实际使用的软件或 API 服务",
  "model": null,
  "parameters": {},
  "parameters_note": "界面未提供模型标识、temperature、top_p 等参数，无法取得的项目未猜测",
  "prompt_files": ["ai_usage/B/prompts/B-20261027-01.md"],
  "calls": null,
  "interactions": 3,
  "input_tokens": null,
  "output_tokens": null,
  "cost": {
    "kind": "unknown",
    "amount": null,
    "currency": null,
    "basis": "订阅工具未提供本会话的实际计费或可核实用量"
  },
  "result": "partial",
  "source_id": "B-local-session-20261027-01",
  "notes": "本段开发未结束；仅记录已知的 3 次成员输入，不代表内部模型请求数"
}
```

账本顶层的 `schema_version`、`role` 保持原值。`coverage_note` 说明从何时开始记录，以及是否漏记历史会话；`records` 内追加上述实际条目。所有时间带时区。

| 字段 | 填写口径 |
| --- | --- |
| `model` | 界面或接口实际提供的模型标识；只有产品名时把产品名记在 tool，模型填 null，在 notes 说明；换模型分条记录 |
| `parameters` | 实际发送或界面明确显示的参数，可包含 temperature、top_p、max_tokens、reasoning_effort；未暴露时用空对象并在 parameters_note 说明，不能把“默认值”猜成实测值 |
| `prompt_files` | 本人实际提示词、追问、错误反馈及修正请求的 Markdown 文件；标明所用任务文件和附件；平台隐藏指令不可取得时直接注明，不虚构完整上下文 |
| `calls` | 可核实的模型请求尝试数，包括真实发出的失败、重试和修正请求；不知道内部次数时用 null，不将聊天轮次或工具调用数视作模型请求数 |
| `interactions` | 可核实的成员输入轮次，无法核实时用 null；与 calls 分别统计 |
| `input_tokens/output_tokens` | 服务或工具提供的实际用量，未知为 null；没有用量不根据文本长度冒充实测 |
| `cost` | kind 为 actual（可核实支出）、estimate（有计价依据的估算）或 unknown；已知数值同时写币种 CNY/USD 等和依据，未知 amount 为 null |
| `source_id` | 可复查的会话片段标识；拿不到平台会话 ID 时生成本人唯一编号；同一会话换模型时加片段后缀；项目请求必须使用原始日志中的 run_id 和请求序号 |
| `result/notes` | succeeded、failed 或 partial；说明具体产物、错误与修正，以及获取不到的字段 |

已确认本次确实免费时，才可登记 `actual / 0 / 币种` 并给出依据。订阅费不能直接算成本次 0 元，也不任意平摊为单次费用。价格推算属于 estimate，写明单价、价格来源与日期、token 和公式；actual 与 estimate 不重复相加。不同币种不直接相加。

提示词保留实际可见内容。提交前移除密钥、鉴权头、Cookie 和个人敏感信息，用 `[REDACTED:原因]` 标注删改；原始私密记录本地保管。公开账本不放 API 密钥。自动检查只做基础结构和部分凭据格式检查，不能代替本人审阅。

## 校验与交接

以 B 为例：

```powershell
python scripts/summarize_ai_usage.py --role B --check --require-records
python scripts/check_delivery.py --role B --submit
```

正式模块交接时账本至少有一条真实记录；交付工具会核对本人账本及提示词引用。未知次数、成本和参数允许如实保留，不因缺少计费数据而阻止开发。账本不是实验成功证明，真实模型验收仍必须有项目运行证据。

## D 的最终汇总

合并四个成员分支和 C 的项目请求记录后执行：

```powershell
python scripts/summarize_ai_usage.py --check --require-records
python scripts/summarize_ai_usage.py
```

产物为 `outputs/ai_usage/summary.md` 和 `summary.json`，按成员、模型及开发/运行范围统计；实际费用、估算、币种分别汇总，单独列出未知次数和未知成本的记录数。ID 或 source_id 重复会报错；脚本不会填补缺失值、调用模型或联网查价。已知小计不能写成完整总量。

最终提交包增加 `AI使用记录/`，放入四人的账本、提示词目录及汇总文件；完整真实运行目录仍放在运行记录中。报告用一张表摘要：成员、模型、可获知参数、提示词位置、已知请求数、未知项、已知费用及依据。**开发中使用 AI 编程不能替代至少一次真实智能体运行。**

启用前的历史记录能从聊天导出或账单核实的才补录；无法恢复的标明未覆盖，不编造日期、次数、模型或成本。
