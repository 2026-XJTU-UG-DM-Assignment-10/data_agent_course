# 成员 A 交接记录

2026-11-02功能补全：D按本次用户授权扩展numeric_summary的q25/q75/iqr/skew，复用原有合法训练数值视图，排除缺失/解析失败/越界值；不足3行偏度为null。冻结契约不变，新增6项独立期望值检查；开发使用记录在D-20261102-adaptive-features，不代填A开发账本。

协作协议：2.0；业务契约：1.0；当前状态：ready_for_review（自测通过，`check_delivery --role A --submit` 通过，待 D 复验）。

## 完成内容和修改文件

新增/修改的本人归属文件：

| 文件 | 内容 |
| --- | --- |
| `scripts/prepare_data.py` | 真实获取 UCI Adult `adult.data`；固定种子 42 抽 10,000 条；按 SHA-256 特征签名分组划分（训练/测试组不相交）；只向训练集注入四类问题；写出 7 个正式路径 |
| `src/profiler.py` | `profile_data(df, *, dataset="train", stage="before") -> QualityReport`，调用 B 的 `normalize_frame`，不另写解析 |
| `checks/check_A.py` | 54 项断言，支持 `--integration`；用独立重算校验计数，不硬编码样例数字 |
| `docs/data.md` | 数据来源、许可、抽样/划分/注入参数、检测结果、复现命令 |
| `handoffs/A.json`、`docs/handoff_A.md` | 本文件与机器可读状态 |
| `evidence/A/fixtures.json`、`evidence/A/formal_data.json` | 脱敏验证摘要 |
| `ai_usage/A/usage.json`、`ai_usage/A/prompts/A-20261028-session.md` | AI 使用账本与本会话提示词 |

生成的正式数据（`.gitignore` 排除，需另打包）：`data/raw/adult.data`、`data/raw/adult.zip`、`data/reference/train_reference.csv`、`data/reference/test_reference.csv`、`data/dirty/train_dirty.csv`、`data/manifests/split_manifest.csv`、`data/manifests/injection_manifest.csv`、`data/manifests/preparation_summary.json`。

未修改：`src/schema.py`、`src/contracts.py`（冻结）、`src/normalization.py`（B）、其他成员文件。

## 运行命令

```powershell
python scripts/prepare_data.py --seed 42 --sample-size 10000
python checks/check_A.py
python checks/check_A.py --integration
python scripts/check_delivery.py --role A --submit
```

## 实际结果与证据

| 项目 | 结果 |
| --- | --- |
| `python scripts/prepare_data.py --seed 42 --sample-size 10000` | 成功。参考记录 10,000；训练 7,000 / 测试 3,000；组交集 0；`train_dirty.csv` 7,140 行 |
| 注入实况 | 异常 70 行、缺失 4,857 格、格式 1,198 格、重复 140 行 |
| 原始文件 | 3,974,305 字节，SHA-256 `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`，保留未改写 |
| `python checks/check_A.py` | 退出码 0，fixtures 与 formal_data 均 passed，54 项断言 |
| `python checks/check_A.py --integration` | 退出码 0，强制使用 B 的真实 `normalize_frame`，54 项断言 |
| 缺正式数据时的行为 | 退出码 2，打印准备命令，不自动下载、不使用假数据 |
| 缺 B 模块时的行为 | 非 `--integration`：打印 `TEST_DOUBLE` 警告后使用具名替身；`--integration`：退出码 2 并说明原因 |
| 检测结果（train_dirty） | 7,140 行；重复 140；异常 70 格 / 70 行；格式 1,218 格；解析失败 0；原始缺失 5,815 格 |

验证范围：

- **fixtures**：passed。共享小样本上缺失 2、重复 1、异常 2 格 1 行、格式 1，与 `quality_report_example.json` 一致；另用合成用例覆盖不可解析值、单位后缀、外围空格和越界。
- **formal_data**：passed。真实下载并准备后核验规模、分组、注入记录、原始文件哈希、标签未改、测试集未注入。
- **real_llm**：not_run，属 C 范围，A 不声称。
- **end_to_end**：not_run，需四模块集成后由 C/D 验收。

## 与公共口径一致的关键点

- `missing_by_column` 只统计原始缺失（实际空值 + 缺失标记），不含解析失败产生的缺失。
- `duplicate_rows` 基于规范化视图按 14 特征 + 标签判定，元数据不参与。
- `outlier_cells` 只计成功解析且越界的数值格；`fnlwgt` 下界为开区间。
- `format_issue_cells` 同一格只计一次；普通数字字符串不算格式问题。
- `numeric_summary` 排除缺失、解析失败和越界值；样本不足时 `std` 为 `null`。
- 四类计数可以重叠，未相加当作问题总行数。

## AI 使用记录

账本 `ai_usage/A/usage.json`，提示词 `ai_usage/A/prompts/A-20261028-session.md`。本次为 DClaw 客户端的开发辅助会话，界面未提供模型请求数与 token 用量，相应字段为 `null`，费用记为 unknown，不按 0 处理。

## 已知问题和下一步

1. **D 复验**：合并后由 D 在 main 执行 `python scripts/check_delivery.py --role A --integration`，再跑 `scripts/check_integration.py --mode rules`。A 的 `real_llm` 与 `end_to_end` 保持 not_run，由 C/D 的真实调用和完整流程验收负责。
2. **B 的目录名问题（不属于 A，仅提醒 D）**：`ai_usage/B/ prompts/` 目录名带前导空格，与 B 账本里 `ai_usage/B/prompts/` 的引用不一致，会让 `check_delivery.py --foundation` 全局失败并阻塞所有人 `--submit`。A 只在本地 `.git/info/exclude` 临时绕过，未修改 B 的文件，也未提交任何绕过。
3. **`.venv` 已在本机创建**，未纳入版本控制；他人按 README 自建。
4. **数据不随 Git 提交**：`data/` 下正式数据与 `outputs/` 均被 `.gitignore` 排除，课程打包时需单独提供，或按 `docs/data.md` 的固定命令重建。
5. `capital_gain`/`capital_loss` 中位数为 0，均值受长尾影响，可作为报告里“为什么需要模型选择填补策略”的论据。

本记录在最后一次交付检查前定稿；`ready_for_review` 状态与 `last_gate` 由 `check_delivery.py --role A --submit` 实际写入，未手工填写。

## 2026-10-30 main 集成复验补记（D）

保留上述成员原始记录；本次用户授权合并初版，由 D 在 main 使用真实依赖复验。具体改动、提交来源、验证边界和证据见 `docs/integration_20261030.md`。新的 handoffs JSON 复验标记由集成人登记，不代表成员此前执行过缺失的 submit 命令。真实模型凭据缺失，LLM 验收仍待完成。

---

# 第二阶段交接（2026-11-01）

本段覆盖第二阶段任务 A1–A4 的实际执行，与上方初版记录并列保留。

## 本次完成项

| 任务 | 结果 |
| --- | --- |
| A1 同步 main | `member-a-data` 落后 main 23 个提交，已 `fetch` + `merge`；解决 6 处冲突 |
| A1 正式数据复现 | 本机执行固定命令，规模与注入计数与基线完全一致 |
| A1 可复现性核验 | 5 个产物 SHA-256 与 `preparation_summary.json` 逐项匹配 |
| A1 自测 | `check_A.py` 与 `--integration` 均退出码 0，54 项 |
| A2 审核 data.md | 逐条核对 D 补写的 10 条，发现 1 处遗漏、2 处未解释差值，已补 |
| A3 报告素材 | `docs/data.md` 重写为 9 节，含规模表、四类问题表、5 张图表建议、3 个必答问题 |
| A4 交接与账本 | 更新本文件、`handoffs/A.json`、新增 `ai_usage/A/prompts/A-20261101-session.md` |

## 合并冲突处理（逐项）

| 文件 | 处理方式 | 理由 |
| --- | --- | --- |
| `scripts/prepare_data.py` | 取 main 版 | main 加了 `newline="\n"`，修复 Windows 下 `write_text` 把 `\n` 转 `\r\n` 导致产物哈希漂移 |
| `docs/data.md` | 以 main 版为底稿后重写 | 保留 D 补写来源与历史，再补全为报告素材 |
| `docs/handoff_A.md` | 手工合并 | 保留成员记录与 D 的 2026-10-30 补记，追加本段 |
| `handoffs/A.json` | 手工合并 | 证据列表合并两侧，保留 `last_gate` 与 `integration_review` |
| `evidence/A/fixtures.json` | 取 main 版 | 两版内容相同，仅行尾差异 |
| `evidence/A/formal_data.json` | 取 main 版 | 同上 |

没有一律选 ours/theirs，也没有丢弃任何一侧的有效记录。

## 本次实际运行结果

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `python scripts/prepare_data.py --seed 42 --sample-size 10000` | 0 | 参考 10,000 / 训练 7,000 / 测试 3,000 / dirty 7,140；组交集 0 |
| `python checks/check_A.py` | 0 | fixtures + formal_data passed，54 项 |
| `python checks/check_A.py --integration` | 0 | 强制真实 `normalize_frame`，54 项 |

产物 SHA-256 全部匹配：`train_reference.csv`(7,000)、`test_reference.csv`(3,000)、`train_dirty.csv`(7,140)、`split_manifest.csv`(10,000)、`injection_manifest.csv`(6,265)。

清洗复算（真实 `clean_training_data` + `plan_rules.json`）：7,140 → 7,000，填补前删 140 行、填补后删 0 行、格式修改 1,218、非法置空 70、填补 5,780，清洗后四类问题均为 0。

## A2 发现并修正的事实问题

1. D 补写文档只说“参考数据保留原生缺失”，**漏了 `train_reference.csv` 的 3 行原生完全重复**。这解释了训练组数 6,997 比行数 7,000 少 3。
2. 检测值 `format_issue_cells` 1,218 比注入 1,198 多 20，`missing` 5,815 比“原生 853 + 注入 4,857”多 105——都是 140 条复制行带入的。原文未说明，容易被误判为计数错误，已在 `docs/data.md` 第 4.3 节写明。
3. 原文未区分“原生问题 / 人工注入 / 最终检测”三种口径，已拆成第 4.1–4.4 节。

## 环境限制（如实记录，未绕过）

本机 `.venv` 为 Python 3.14.5，`requirements.txt` 基线是 3.13.9。`scikit-learn` 依赖的 `scipy` 在 3.14 无预编译包，**无法安装**。

- 不影响 A：`prepare_data.py`、`src/profiler.py`、`checks/check_A.py` 仅依赖 pandas / numpy / pydantic，均可用。
- 影响面仅在 D 的分类与页面（需 sklearn / streamlit）。本机未尝试安装、也未声称安装成功。

## 未执行项

- `check_delivery.py --role A --integration` 与 `check_integration.py`：按任务划分由 D 在 main 执行，A 不执行。
- `real_llm` / `end_to_end`：属 C/D 范围，A 未配置凭据，保持 `not_run`。

## AI 使用记录

账本 `ai_usage/A/usage.json` 新增 `A-20261101-session`；提示词 `ai_usage/A/prompts/A-20261101-session.md`。模型、token、费用均未知，按规范留 `null`，未记为 0。

## 下一步

1. 本人在 `member-a-data` 执行 `summarize_ai_usage.py --role A --check --require-records` 与 `check_delivery.py --role A --submit`，通过后推送本人分支。
2. 由 D 合并并在 main 复验。
3. D 可直接使用 `docs/data.md` 第 8 节的幻灯片要点、图表建议与三个必答问题。
