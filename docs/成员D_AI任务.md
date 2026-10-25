# 成员 D：可直接交给 AI 的任务

请先阅读原《数据处理智能体_AI开发任务书》及本包全部公共约定，然后实施分类、界面、CLI、集成与提交材料整理。

## 我负责的文件

- `src/classifier.py`、`app.py`、`src/cli.py`、`scripts/smoke_check.py`
- 公共 `src/schema.py、src/contracts.py` 的统一维护
- README、依赖文件、配置示例、忽略规则
- `docs/acceptance.md、docs/handoff_D.md`，以及报告和 PPT 的最终汇总。

不要另写检测、清洗和模型接口。总流程 `src/pipeline.py` 由 C 维护，页面和 CLI 只调用它。

## 必须完成

1. 将本包 starter 公共代码和小样本同步给全员，统一接口版本与依赖。已有代码先核对，不直接覆盖。
2. 实现 `train_and_evaluate(clean_train, clean_test, *, output_dir, seed=42) -> ClassificationResult`。
3. 显式选择 14 个特征，训练拟合 StandardScaler/OneHotEncoder/LogisticRegression；测试只转换，未知类别可接受，来源 ID 与标签不进特征。
4. 固定标签顺序，输出真实 Accuracy、Macro-F1 和 2×2 混淆矩阵，保存图片。
5. 实现 Streamlit 演示入口、明确模式、执行按钮、策略与前后统计、指标和下载；页面重绘不能再次调用模型。
6. 实现 CLI，默认路径采用公共说明；返回失败时以非零进程退出码和明确错误提示结束。
7. 汇总各模块，只修复本人或公共文件。其他业务缺陷附最小案例交对应成员，不在页面绕过公共接口。
8. 编写有意义的 smoke 检查并逐项记录真实结果；正式数据规模与小样本联调分开。

## 交付与时间

第 1 天同步公共文件，第 3 天交可用分类函数，第 4 天参与规则流程联调，第 8 天交完整页面和 README。

第 9 天汇总其他成员的真实报告素材、PPT 页面和贡献说明；第 10 天按 README 在新终端复现并打包，不包含密钥、虚拟环境或缓存。将已完成、待验证和缺失的正式文件如实列出。
