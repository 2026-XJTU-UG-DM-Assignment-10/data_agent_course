# 成员 D：可直接交给 AI 的任务

从 `docs/START_HERE.md` 进入，先读协作协议 2.0、`collaboration/roles.json`、公共契约 1.0 和四份交接，再实施分类、界面、CLI 与异步集成。可直接复制的开工词见 `prompts/D.md`。

## 我负责的文件

- `src/classifier.py`、`app.py`、`src/cli.py`、`scripts/smoke_check.py`
- 公共 `src/schema.py、src/contracts.py` 的统一维护
- README、依赖文件、配置示例、忽略规则
- `docs/acceptance.md、docs/handoff_D.md`，以及报告和 PPT 的最终汇总。
- `handoffs/D.json`、`checks/check_D.py`、`docs/classification.md` 和 `examples/role_D/` 中本人新增测试样例。

不要另写检测、清洗和模型接口。总流程 `src/pipeline.py` 由 C 维护，页面和 CLI 只调用它。

## 必须完成

1. 公共代码和样例已准备，确认全员使用同版本，无需再次复制 starter。维护公共文件时遵守冻结约定，不修改哈希绕过检查。
2. 实现 `train_and_evaluate(clean_train, clean_test, *, output_dir, seed=42) -> ClassificationResult`。
3. 显式选择 14 个特征，训练拟合 StandardScaler/OneHotEncoder/LogisticRegression；测试只转换，未知类别可接受，来源 ID 与标签不进特征。
4. 固定标签顺序，输出真实 Accuracy、Macro-F1 和 2×2 混淆矩阵，保存图片。
5. 实现 Streamlit 演示入口、明确模式、执行按钮、策略与前后统计、指标和下载；页面重绘不能再次调用模型。
6. 实现 CLI，默认路径采用公共说明；返回失败时以非零进程退出码和明确错误提示结束。
7. 汇总各模块，只修复本人或公共文件。其他业务缺陷附最小案例交对应成员，不在页面绕过公共接口。
8. 编写有意义的 smoke 检查并逐项记录真实结果；正式数据规模与小样本联调分开。

## 交付与时间

用 `clean_train_small.csv、clean_test_small.csv` 独立训练分类器，用显式标记的示例指标/RunResult 开发页面，不等待 B/C。第 3 天交分类函数；第 4/6/8 天按协议独自执行规则、模型、页面技术检查，问题异步退回对应负责人。

第 9 天汇总其他成员的真实报告素材、PPT 页面和贡献说明；第 10 天按 README 在新终端复现并打包，不包含密钥、虚拟环境或缓存。将已完成、待验证和缺失的正式文件如实列出。

## 固定自测、集成和交付

实现 `checks/check_D.py`，支持 `--integration`：真实训练干净小样本，验证未知类别、固定矩阵顺序和正确特征选择；页面可测试展示逻辑，CLI 返回码可测试错误输入。示例 JSON 不能作为本人的真实分类结果。

本人功能通过后执行 `python scripts/check_delivery.py --role D --submit`。集成时在 main 使用 `--role X --integration` 复验各人；在 `docs/integration_log.md` 记录接受/退回，错误附最小复现交原负责人。

本人默认自测把脱敏摘要写入 `evidence/D/` 并提交；`--integration` 自测只写 outputs，不重写其他成员或本人的已提交摘要。各成员的原始输出不在 Git 中，正式数据可按 A 的准备命令重建，不依赖队友手动发送本机目录。

实现 `scripts/smoke_check.py --mode rules|llm --report PATH`，按协议生成真实模块、正式数据、对应模型模式和证据路径的报告。之后用 `python scripts/check_integration.py --mode rules`、`--mode llm` 运行检查。不得仅填写 uses_real_modules=true 等标志而不实际执行相应流程。

## 本人 AI 使用记录

按 [AI 使用记录规范](AI使用记录规范.md)维护 `ai_usage/D/usage.json` 和本人提示词文件，每段实际开发会话及时更新，交接前核对模型、参数、次数、费用和未知项。不要修改其他人的账本，也不要用开发辅助记录替代项目实际运行证据。

合并四人的账本后运行 `python scripts/summarize_ai_usage.py --check --require-records`，再运行不带参数的汇总命令。账本、脱敏提示词与 outputs/ai_usage/ 下两份汇总一起打包；各成员仍负责核实本人记录。
