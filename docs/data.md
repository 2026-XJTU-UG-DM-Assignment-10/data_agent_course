# 数据说明（成员 A）

本文件是报告第 2 节的素材来源，所有数字取自本机实际运行产物，不是示意值。

## 1. 数据来源

| 项目 | 内容 |
| --- | --- |
| 数据集 | UCI Adult（Census Income），48,842 条记录的官方说明版本 |
| 官方页面 | <https://archive.ics.uci.edu/dataset/2/adult> |
| 实际下载地址 | <https://archive.ics.uci.edu/static/public/2/adult.zip> |
| 许可 | CC BY 4.0 |
| 引用 | Becker, B. and Kohavi, R. (1996). Adult. UCI Machine Learning Repository. <https://doi.org/10.24432/C5XW20> |
| 原始文件 | `data/raw/adult.data`，3,974,305 字节 |
| 原始文件 SHA-256 | `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d` |

下载的 zip 同时保留为 `data/raw/adult.zip`。原始文件未被改写，报告与复现均以该 SHA-256 为基准。

说明：官方 `adult.data` 包含 32,561 条训练侧记录；任务书里 48,842 是含 `adult.test` 的总量。本项目按任务书允许的方式只用 `adult.data`，不合并测试文件。因此参考池为 32,561 条，仍远大于 10,000 的抽样规模。

## 2. 解析与参考池

- 逐行按 15 个官方字段解析（14 特征 + `income`）。
- 字段外围空格统一去除；标签末尾句点去除（`<=50K.` → `<=50K`）。
- 合法标签只有 `<=50K`、`>50K`，其余记录排除并计数。

| 指标 | 实际值 |
| --- | --- |
| 原始记录行 | 32,561 |
| 标签非法被排除 | 0 |
| 字段数不符被排除 | 0 |
| 参考数据池 | 32,561 |

参考池仍含原生缺失（`?`）与原生重复组合，不能称为“完全干净的真值”。

## 3. 抽样与分组划分

- 随机种子固定为 `42`，从参考池无放回抽取 10,000 条。
- 分组签名 `_group_id`：对规范化后的 14 个特征做确定性序列化后取 SHA-256 前 16 位，不用跨进程不稳定的 `hash()`。
- 划分按整组分配：同一个 `_group_id` 只会落入训练或测试之一，保证两端 `_group_id` 集合不相交。
- 目标训练占比 70%。

| 指标 | 实际值 |
| --- | --- |
| 参考记录 | 10,000 |
| 训练集 `train_reference.csv` | 7,000 |
| 测试集 `test_reference.csv` | 3,000 |
| 训练组数 | 6,997 |
| 测试组数 | 3,000 |
| 训练/测试组交集 | 0 |

训练组数少于训练行数，说明存在特征签名完全相同的记录（同一组内多条），这些记录被整体保留在同一侧，没有跨集合泄漏。训练规模 7,000 > 5,000，满足课程要求。

测试集不注入任何人为问题，但仍会经历格式规范化与必要的缺失处理；填补参数只允许从训练集学习。

## 4. 训练集问题注入

只修改 14 个特征单元格，`income`、`_source_id`、`_group_id` 一律不动。各类问题尽量不落在同一单元格，重复行在最后复制，因此副本会带上其来源行的全部已注入问题。

| 类型 | 构造规则 | 实际数量 |
| --- | --- | --- |
| 异常值 | 约 1% 训练行，年龄改 `-5`/`999`，或周工时改 `0`/`999` | 70 行 |
| 缺失值 | 约 5% 的非缺失特征单元格写入 `?` | 4,857 格 |
| 格式问题 | 约 3% 的非缺失数值单元格加外围空格或 ` years`/` hours` 后缀 | 1,198 格 |
| 重复数据 | 约 2% 训练行整行复制，保留来源 ID | 140 行 |

| 指标 | 实际值 |
| --- | --- |
| 训练参考行 | 7,000 |
| `train_dirty.csv` 行 | 7,140 |
| `injection_manifest.csv` 事件行 | 6,265 |
| 测试集注入 | 0 |

`injection_manifest.csv` 只用于构造审计和离线核查，不传给模型、不参与填补或分类，也不作为检测答案。

## 5. 质量检测结果

`profile_data(train_dirty.csv, dataset="train", stage="before")` 的实际输出，与 `checks/check_A.py` 中独立重算的结果完全一致。

### 5.1 总体计数

| 指标 | 值 | 说明 |
| --- | --- | --- |
| `row_count` | 7,140 | 含重复行 |
| `feature_count` | 14 | 不含标签与两个元数据字段 |
| `duplicate_rows` | 140 | 按 14 特征 + 标签判定，与注入的 140 条复制行一致 |
| `outlier_cells` | 70 | 每行只注入 1 个越界值 |
| `outlier_rows` | 70 | 行不重复计数 |
| `format_issue_cells` | 1,218 | 注入 1,198 + 复制行带入 20 |
| `parse_error_cells` | 0 | 注入的格式问题都是可解析的，没有制造不可解析值 |

注意：这五类问题可以重叠，相加不等于“有问题总行数”，本表**不**提供问题行合计。

`format_issue_cells` 比注入数多 20，是因为 140 条复制行中有 20 个格式脏单元格被原样带入副本。这一点在检测口径里是正确的：计数针对当前表，不针对“原始来源行”。

### 5.2 逐列原始缺失

| 列 | 缺失数 |
| --- | --- |
| age | 341 |
| workclass | 706 |
| fnlwgt | 389 |
| education | 370 |
| education_num | 306 |
| marital_status | 341 |
| occupation | 676 |
| relationship | 362 |
| race | 386 |
| sex | 357 |
| capital_gain | 331 |
| capital_loss | 351 |
| hours_per_week | 400 |
| native_country | 499 |

以上合计 5,815 格，由三部分构成：原生缺失 853 格、人为注入 4,857 格、复制行带入的缺失约 105 格。口径是“原始缺失数量”，因此解析失败产生的缺失不计入此列。

### 5.3 六个数值字段摘要

在规范化视图上排除缺失、解析失败和越界值后计算，供 C 制定计划。

| 字段 | count | mean | median | min | max | std |
| --- | --- | --- | --- | --- | --- | --- |
| age | 6,765 | 38.64 | 37.0 | 17.0 | 90.0 | 13.32 |
| fnlwgt | 6,751 | 189,511.32 | 177,727.0 | 12,285.0 | 1,268,339.0 | 105,828.58 |
| education_num | 6,834 | 10.10 | 10.0 | 1.0 | 16.0 | 2.55 |
| capital_gain | 6,809 | 1,142.02 | 0.0 | 0.0 | 99,999.0 | 7,764.34 |
| capital_loss | 6,789 | 87.50 | 0.0 | 0.0 | 3,683.0 | 400.37 |
| hours_per_week | 6,704 | 40.49 | 40.0 | 1.0 | 99.0 | 12.38 |

`capital_gain`/`capital_loss` 的中位数都是 0，均值被长尾明显拉高，这正是“均值还是中位数”值得交给模型判断的依据；规则模式固定取中位数。

## 6. 复现

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts/prepare_data.py --seed 42 --sample-size 10000
.venv\Scripts\python.exe checks/check_A.py
.venv\Scripts\python.exe checks/check_A.py --integration
```

网络不可达时，手动下载 <https://archive.ics.uci.edu/static/public/2/adult.zip>，解压出 `adult.data` 放到 `data/raw/adult.data` 后重新执行准备命令。脚本不会生成替代数据。

固定种子 42 与固定抽样/划分顺序保证同一份原始文件可产出完全相同的五个 CSV，SHA-256 见 `data/manifests/preparation_summary.json`。
