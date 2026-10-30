# D 分类与展示实现

## 当前状态（2026-10-30第二阶段）

初版已在main完成集成，不再缺A/B/C。当前复用原分类/页面/CLI，没有据测试集调参。正式rules运行20261030T070819Z-7779c942：7140→7000训练、3000测试，Accuracy0.8523333333、Macro-F1 0.7888456818，矩阵[[2101,189],[254,456]]。本轮正式smoke通过；人工浏览器核对了质量、理由、指标、13下载控件、三份实际文件、选择器不新增运行和失败清旧指标。真实模型由用户确认尚未配置，保持待验。

报告6页/PPT7页使用同一run_id；PDF逐页渲染检查，PPT结构/字体/原生表格/重导入和逐页图像检查通过，原生PowerPoint操作未执行。下面保留初版的实现与验证历史，不再将其“缺上游”描述用作当前状态。

## 初版实现与验证历史（2026-10-26）

本次开发基于 2325930，在 member-d-ui 分支完成。冻结契约 1.0 未修改，其他成员业务与账本未修改。

## 分类边界

`src/classifier.py:train_and_evaluate` 接受已经清洗的 DataFrame，返回公共 `ClassificationResult`。输入需含公共 17 列；额外列可以存在，但明确只选择 `FEATURE_COLUMNS` 中的 14 列用于训练和预测。

六个数值特征使用 StandardScaler，八个类别特征使用 OneHotEncoder(handle_unknown="ignore")，分类器为 LogisticRegression(random_state=seed, max_iter=2000)。整个 sklearn Pipeline 只在训练集 fit，测试集只 predict。不使用测试结果选择参数。收敛警告会使运行失败，需在正式数据集成后据实际情况处理。

不执行清洗、不填补、不修改原表。拒绝空表、缺列、重复列、无效标签、训练仅单类、残余缺失、未规范化类别、非数值/布尔/复数数值列、非有限/范围非法数值、训练特征+标签重复和训练测试来源组交叉。测试可仅含一个标签，仍返回固定 2×2 矩阵。训练/测试标签与元数据从不成为特征；元数据仅参与审计边界检查。

Accuracy 和 Macro-F1 返回 0–1 数值。Macro-F1 是固定两个类别各自 F1 的等权平均；缺少某类预测或真实样本时使用 zero_division=0。矩阵行是真实标签、列是预测标签，顺序固定 `<=50K, >50K`。唯一分类输出为传入目录中的 `confusion_matrix.png`，返回其绝对路径；其余 JSON/CSV/日志由 C 导出。

## 页面与 CLI

`app.py` 和 `src/cli.py` 共用 C 的公共 `run_pipeline`。CLI 默认输入为 `data/dirty/train_dirty.csv` 和 `data/reference/test_reference.csv`；支持 --mode、--train、--test、--output-dir、--seed。运行失败/缺输入退出 1，参数非法退出 2，成功退出 0。只有缺失的 `src.pipeline` 会被报告为未交付，已有模块的导入/运行错误不会被替身覆盖。

页面仅显式点击开始才创建运行，RunResult 保存在 session_state；重绘、模式选择和下载不再次调用流程。结果模式与当前选择分别显示。新运行失败会清除旧成功结果；失败结果不展示指标。页面从真实导出读取质量前后统计、策略/理由、审计数量、指标、矩阵与下载；文件路径限制在该次输出目录内。执行中显示流程状态，具体工具事件仍以 C 的 events.jsonl 为准，尚未实现逐工具实时进度回调。

页面约定使用公共示例的 artifact 逻辑名称：quality_before、quality_after、cleaning_plan、audit_train、audit_test、confusion_matrix；其他已声明 artifact 同样生成下载入口。正式 smoke 要求补齐 cleaning_state、metrics、run_result、summary、events、train_processed、test_processed。接入 C 的真实实现后必须复核逻辑名称与日志字段是否一致，不能绕过契约。

## 实际验证（2026-10-26）

命令：`.venv\Scripts\python.exe checks/check_D.py`。实际训练共享人工样例 7 行、测试 3 行（含未知工作类别）。结果：Accuracy=0.0，Macro-F1=0.0，矩阵 `[[0,1],[2,0]]`。本样例很小且非正式数据，无准确率门槛；没有依据测试结果改参数或编造提升。页面合成预览中的 66.67% 来自原有示例 JSON，与本次实测无关。

自测直接检查训练均值、编码类别与特征列，独立重算矩阵/Accuracy/Macro-F1；检查输入不变、额外标签副本与 ID 不影响结果、单类测试、PNG 有效、15 类无效输入。Streamlit AppTest 检查质量表、策略理由、审计、成功/失败、旧指标清理、模式切换及重绘不重复执行；CLI 检查真实子进程错误退出码。只有缺失 C 时，UI/CLI 接线使用脚本内明确标记的 C 测试替身，分类器始终真实训练。已有 C 模块会被实际调用，错误不得用替身掩盖。

浏览器实际启动 `.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false`，检查合成标识、成功下载示例 SVG，以及真实入口提示 C 尚未交付。截图：outputs/member_D/browser_preview.png、browser_missing_pipeline.png；交互记录：outputs/member_D/browser_check.json。这不是正式流程成功截图。

## 集成检查边界

`scripts/smoke_check.py --mode rules|llm --report PATH` 只接正式数据和真实模块。实际成功前检查正式规模、来源关联、分组隔离、四类问题；运行后检查导出、数据规模与清洁度、测试标签/ID/顺序、输入文件哈希、指标一致和事件序列。规则模式拒绝 llm_request 事件；模型模式要求 1–2 次实际请求、成功返回、模型/参数/原始文本及实际提示词日志。事件 payload 中的 LLMReply 对象与 prompt/messages 可嵌套，按递归发现；C 交付后需以真实日志复验该约定。

当前 smoke 的成功路径尚未验证：缺 A/B/C 模块和正式数据。已验证缺前置条件时重新写 not_ready 报告并退出 2；不会复制示例或保留旧成功。受控错误 JSON/重试/缺凭据的真实流程验证由 C 自测与最终集成共同覆盖，目前待验证。
