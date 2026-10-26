# 成员 A：可直接交给 AI 的任务

从 `docs/START_HERE.md` 进入，先读协作协议 2.0、`collaboration/roles.json` 的 A 条目和公共契约 1.0，再实施数据与检测。读取本人交接和 D 的退回记录，继续未完成项，不依赖聊天历史。可直接复制的开工词见 `prompts/A.md`。

## 我负责的文件

- `scripts/prepare_data.py`
- `src/profiler.py`
- `docs/data.md`
- `docs/handoff_A.md`
- `handoffs/A.json`、`checks/check_A.py`、`examples/role_A/` 中本人新增测试样例。
- `data/raw、data/reference、data/dirty、data/manifests` 中由准备脚本生成的文件。

不要实现或重写其他成员的清洗、模型接口、分类、页面、总流程。公共文件由 D 维护；需要变更时提出具体差异。

## 必须完成

1. 真实获取 UCI Adult 的 `adult.data`，保留原始文件、来源和许可说明；网络失败时提供手动放入路径，不用生成数据冒充。
2. 使用固定种子 42，按任务书准备 10,000 条参考记录，按特征签名分组划分，训练和测试 `_group_id` 不相交。
3. 只向训练集注入四类问题，保留来源 ID、分组 ID、划分记录和注入记录；复制行保留来源关联。
4. 输出公共说明规定的正式 CSV 和 manifest 路径，验证清洗前训练规模大于 5,000。
5. 实现 `profile_data(df, *, dataset="train", stage="before") -> QualityReport`，调用 B 的 `normalize_frame`；不要另写一套格式解析。
6. 严格采用公共统计口径，输出全部 14 个特征的缺失统计和六个数值字段的摘要。
7. 使用公共小样本和冻结计数口径独立验证；不要求和 B 同时在线，不用 manifest 当检测结果。

## 交付与时间

第 1 天固定字段和路径，第 3 天交准备脚本、正式数据、检测函数和实际调用命令。使用 `normalized_train_small.csv` 和 `quality_report_example.json` 开发统计；B 缺失时允许在自测中注入只针对样例的规范化替身，不在正式代码保留第二套解析。B 实现一旦存在，导入或执行错误必须暴露，不用替身掩盖。

在 `handoff_A.md` 写实际文件、命令、样本数、检测结果、依赖和未完成事项；报告素材放入 `data.md`。不要编造下载成功、数据规模或实验结果。

## 固定自测和交付

实现 `checks/check_A.py`，无参数时检查本人业务，支持 `--integration` 强制使用 B 的真实规范化。验证真实准备数据的规模、分组、注入记录与原始文件保留；验证样例的缺失/重复/异常/格式检测，不能只硬编码样例数字。

数据准备使用固定命令 `python scripts/prepare_data.py --seed 42 --sample-size 10000`。自测不应在用户不知情时重新下载数据；缺正式文件时明确输出准备命令并返回非零状态。

完整证据写入 `outputs/member_A/` 和 `data/manifests/`，可提交的脱敏摘要写入 `evidence/A/`；handoffs/A.json 的 fixtures/formal_data.evidence 引用摘要文件。依次执行本人自测、填写交接、`python scripts/check_delivery.py --role A --submit`，通过后再提交个人分支。未下载真实数据时不能把 A 的正式交付标记 ready。

## 本人 AI 使用记录

按 [AI 使用记录规范](AI使用记录规范.md)维护 `ai_usage/A/usage.json` 和本人提示词文件，每段实际开发会话及时更新，交接前核对模型、参数、次数、费用和未知项。不要修改其他人的账本，也不要用开发辅助记录替代项目实际运行证据。
