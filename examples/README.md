# 联调样本说明

这些是人工编写、修改的微型样本，**不是本项目已经下载的官方数据，也不是正式实验结果**。正式展示需由 A 按任务书获取 UCI 数据并构造达标数据集。

- `train_small.csv`：8 行，包含一个多余重复行、两处原始缺失、两处非法数值，以及 `40 hours` 格式问题。两个类别都存在。
- `test_small.csv`：3 行，与训练集来源组不重叠；含训练集中没有的工作类别，用于检查未知类别编码。
- `plan_rules.json`：标记为规则模式的合法计划，可以供 B、D 提前开发。
- `plan_invalid.json`：故意使用不支持的 `knn`，必须被公共模型拒绝，不能自动接受为合法计划。

小样本用于模块联调时允许少于 5,000 行，不能用于证明正式验收的数据规模。分类函数不要把课程规模限制写死在模型内部；正式数据规模由准备脚本和验收检查。

## 协议 2.0 的独立开发输入

统一清单见 `fixtures_manifest.json`，明确标记 `is_experiment=false`。以下样例是人工整理或合成的，不代表业务实现已经运行。

| 文件 | 用途 |
| --- | --- |
| `normalized_train_small.csv` | A 开发规范化后统计；范围非法值保留，原始缺失仍为空 |
| `clean_train_small.csv`、`clean_test_small.csv` | D 不等 B 即可真实训练小样本；训练为 7 行，测试为 3 行 |
| `cleaning_state_example.json` | 中位数+Unknown 计划的参考填补值，供 B 自测、C 接线 |
| `quality_report_example.json` | 合成检测摘要，供 C 独立开发计划生成 |
| `llm_reply_example.json` | 明确命名 TEST_DOUBLE 的模拟返回，只用于受控测试 |
| `classification_result_example.json`、`run_result_example.json` | C/D 开发返回结构和页面，不作为真实指标或成功运行记录 |
| `mock_confusion_matrix.svg` | 明确写有 SYNTHETIC EXAMPLE 的示意矩阵 |

clean_train 的数值填补基于删除原始重复后的训练观测，中位数年龄为 38.5；该参考只适用于现有中位数+Unknown 计划，不能要求所有合法策略产生相同结果。

成员新增不同用例放在 `examples/role_X/`，不要修改这些共享输入来迎合实现。正式流程必须使用真实数据和模块；缺少同伴依赖时允许在独立自测内使用明确标记的替身，集成复验时禁用这类替身。

首次运行样本时，原始缺失应统计为 2 个特征单元格；异常为 2 个单元格、1 行；格式问题为 1 个单元格；重复多余行数为 1。问题类型计数采用公共接口说明的口径，不能把这些数字直接写死进实现。
