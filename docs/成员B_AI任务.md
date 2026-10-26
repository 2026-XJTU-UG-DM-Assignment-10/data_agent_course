# 成员 B：可直接交给 AI 的任务

从 `docs/START_HERE.md` 进入，先读协作协议 2.0、`collaboration/roles.json` 的 B 条目和公共契约 1.0，再实施规范化与清洗。读取本人交接和 D 的退回记录，继续未完成项，不依赖聊天历史。可直接复制的开工词见 `prompts/B.md`。

## 我负责的文件

- `src/normalization.py`
- `src/cleaner.py`
- `docs/cleaning.md`
- `docs/handoff_B.md`
- `handoffs/B.json`、`checks/check_B.py`、`examples/role_B/` 中本人新增测试样例。

不要重写数据准备、质量检测、模型调用、分类、界面或总流程。公共模型直接导入，不另建不兼容字典。

## 必须完成

1. 第 1 天先提供 `normalize_frame(df) -> (DataFrame, NormalizationAudit)`，供 A 检测和本人清洗共用。遵守缺失、单位、类别大小写、标签和元数据规则。
2. 实现 `clean_training_data(train_df, plan) -> (clean_df, CleaningState, CleaningAudit)`。
3. 实现 `transform_test_data(test_df, cleaning_state) -> (clean_test_df, CleaningAudit)`。
4. 训练流程完成规范化、前置去重、非法值置空、训练集填补拟合、填补和最终重复复查；只因重复删除行。
5. 测试流程不学习统计量、不去重、不删行、不改变标签或顺序、不修改 state。
6. 正确处理全缺失数值列的明确失败、类别众数并列、类别全缺失和未支持的数字字符串。
7. 返回公共对象，审计数量按说明计数；不在工具里写另一份全局日志，交给 C 的流程层记录调用。

## 交付与时间

使用 `examples/train_small.csv、test_small.csv、plan_rules.json` 独立开发，不等待正式数据或真实模型。`clean_train_small.csv` 和 `cleaning_state_example.json` 为中位数+Unknown 计划下人工整理的参考输出。第 1 天尽早上传可用规范化函数，第 4 天前交完整清洗和测试转换。

证明输入未被原地修改、测试行数/标签不变、再次规范化不增加格式修改、处理后数据能被 D 分类。交付实际调用命令和审计结果至 `handoff_B.md`，方法解释和清洗案例至 `cleaning.md`。

## 固定自测和交付

实现 `checks/check_B.py`，支持无参数及 `--integration`。用真实清洗函数验证训练重复删除、非法值置空后填补、格式可重复规范化、测试统计不重拟合，以及异常/全缺失列边界。至少增加一个不同于共享八行样例的用例，避免对固定数据硬编码。

完整证据写入 `outputs/member_B/`，可提交的脱敏摘要写入 `evidence/B/`；本人 JSON 的 fixtures.evidence 引用摘要。填写 Markdown 交接，然后执行 `python scripts/check_delivery.py --role B --submit`；通过后再提交个人分支。不得用改共享样例、公共数据结构或空自测让检查通过。
