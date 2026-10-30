# 成员 A 交接记录

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
