# 成员 C：智能体、模型适配与总流程

业务契约：1.0；工作流：2.0。

## 处理流程

`run_pipeline(train_path, test_path, mode, output_dir, seed, llm_client)` 是唯一总流程入口：

1. 读取固定 17 列 CSV，检查字段并保持固定列顺序。
2. 调用 A 的 `profile_data` 分别生成训练、测试集处理前报告。仅训练集报告进入计划生成器。
3. 规则模式直接生成固定规则计划，不访问网络；LLM 模式从环境读取 `LLM_API_URL`、`LLM_API_KEY`、`LLM_MODEL`，使用 OpenAI-compatible Chat Completions 协议。
4. 对模型文本严格解析 JSON，只允许五个决策字段；本地代码设置 `mode="llm"`、契约版本和固定步骤。无效 JSON/字段/取值最多纠正一次，总请求预算最多两次。
5. 调用 B 的训练清洗与测试转换；填补状态只从训练集拟合。随后调用 D 的 `train_and_evaluate`。
6. 输出唯一运行目录，包含 `events.jsonl`、处理前质量报告、计划、清洗状态与审计、清洗后 CSV、混淆矩阵及 `run_result.json`。异常返回 `status="failed"`，并保留错误事件。

## 模型协议与安全

- `LLMClient.generate_plan` 每次调用最多发送一次 HTTP 请求，不做隐藏重试；客户端本身限制 `LLM_MAX_CALLS`，agent 同时限制计划生成最多两次。
- 默认 endpoint 是 `LLM_API_URL` 后追加 `/chat/completions`；若 URL 已以 `/chat/completions` 结尾则直接使用。该接口需由所用服务商实际支持 OpenAI-compatible 请求体。
- 模型只收到白名单训练集摘要：行数、缺失、重复、异常、格式问题、数值摘要及警告。不传测试统计、原始数据、注入 manifest 或元数据 ID。
- 事件记录实际系统提示词、用户摘要/反馈、模型返回文本、模型标识、请求参数、可用 token/成本、计划校验结果、错误与修正。运行日志不包含 API key 或请求鉴权头。完整事件位于本地 `outputs/<run_id>/events.jsonl`，不要公开原始日志前先检查脱敏。
- 真实 `LLMClient` 发起请求时，pipeline 自动在 `ai_usage/C/usage.json` 增加一条 `project_runtime` 记录，并保存对应脱敏请求提示词文件；HTTP 返回后更新模型、token、成本与结果。测试替身不会写入项目运行账本。每次请求使用 `run_id:请求序号` 作为 `source_id`。
- 供应商未返回 token 或费用时保持 `null`；不将未知成本记为零。
- 规则模式与模拟模型均不能算真实模型调用。真实模型验收须使用有效凭据执行 `python checks/check_C.py --real-llm --report outputs/real_llm_check/real_llm_evidence.json`，并由正式 pipeline 完成端到端验收。

## 本地验证

```bash
python checks/check_C.py
python checks/check_C.py --integration
python scripts/check_delivery.py --role C --submit
```

离线自测中的假客户端和 A/D 测试替身只用于验证 C 的控制逻辑与接线，不构成正式数据、真实模型或端到端验收证据。`--integration` 要求 A/B/D 真实模块存在并导入；缺失时以退出码 2 报告待上游交付。
