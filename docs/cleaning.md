# 成员 B：格式规范化与数据清洗

业务契约 v1.0。复用 `src.schema` 公共常量与 Pydantic 类型，不改变冻结接口。

## 数据流与原则
- `normalize_frame(df)`：在独立副本中识别缺失、裁剪类别空格、转换普通数字与允许的单位；保留非法范围的已解析值供 A 检测；数值解析失败设为 NaN。索引/顺序/标签/元数据保持不变。
- `clean_training_data(train_df, plan)`：规范化 → 使用 14 个特征 + income 去重（不含元数据）→ 范围非法数值置空 → 仅从训练记录计算数值均值/中位数与类别众数/Unknown → 填补 → 再去重。仅重复行允许删除。
- `transform_test_data(test_df, cleaning_state)`：规范化 → 范围非法置空 → 只应用训练保存的填补值。绝不去重、拟合、修改状态或更改标签和来源信息。
- 全无有效数值观测抛 `DataValidationError`；类别全缺失采用 Unknown 并在训练审计中警告。众数并列按字符串排序取首项。
- 格式修改单元格、非缺失解析错误、范围置空、填补数量、两轮去重各自独立审计，不相加为“问题行数”。
- 数值范围以 `NUMERIC_BOUNDS` 为准；`fnlwgt` 必须严格大于 0。
- 不写全局日志，不调用 LLM/API；C 在其 pipeline 记录事件。

## 样例复现
运行 `python checks/check_B.py` 或 `python checks/check_B.py --integration`。
共享训练样例由 8 行变成 7 行，首次去重 1 行；age=-5 和 hours_per_week=999 被置空后由训练中位数填补为 38.5、40；字符串单位 `40 hours` 解析成 40；问号工作类别与空教育填为 Unknown。
共享测试样例全部 3 行保留，`Unseen-example-workclass` 不改，不在测试集学习统计量。
参考文件 `examples/clean_train_small.csv` 和 `examples/cleaning_state_example.json` 仅作为离线样例对照，不是实际实验。

## 自测覆盖
重复规范化幂等、输入不可变、重复与二次重复、数值异常与不支持单位、全缺失数值失败、类别全缺失警告、类别众数并列、未知测试类别、重复测试行不删、模型填补状态不变、行序与标签/来源 ID 不变、共享参考样例数值对照。
正式 Adult 数据、真实模型调用、D 分类器和全流程不在 B 的本地小样例通过范围内。
