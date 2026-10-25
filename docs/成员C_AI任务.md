# 成员 C：可直接交给 AI 的任务

请先阅读原《数据处理智能体_AI开发任务书》、本包《公共接口说明》以及 `src/schema.py、src/contracts.py`，然后只实施智能体、模型适配和总流程。

## 我负责的文件

- `src/llm_client.py`
- `src/agent.py`
- `src/pipeline.py`
- `docs/agent.md`
- `docs/handoff_C.md`

不要重写 A 的检测、B 的清洗、D 的分类或页面。公共契约直接使用，模型服务只接一家用户可用的接口。

## 必须完成

1. 第 1 天先实现规则计划入口，不调用外部模型，明确记录 rules 模式。
2. 实现 `get_cleaning_plan(train_report, *, mode, llm_client=None, event_sink=None)`，只接受训练集处理前报告，严格验证白名单计划。
3. 模型客户端实现 `LLMClientProtocol.generate_plan(summary, *, feedback=None) -> LLMReply`，HTTP 协议根据实际可用服务官方文档适配；凭据从环境读取。
4. 每次运行至多两次真实请求，包含纠正错误 JSON；总预算不能被客户端隐藏重试绕过。规则模式不得发请求。
5. 实现公共 `run_pipeline`，调用其他成员的函数；管理运行 ID、事件日志、数据与 JSON 导出、错误状态。
6. 模型只读取训练摘要，不读取测试统计、注入 manifest 或全部原始数据；模式由代码根据真实上下文确定。
7. 日志保留实际提示词、返回、参数、用量、工具执行及错误修正；不写密钥，未知成本用 null。

## 交付与时间

第 4 天跑通规则流程，第 6 天完成真实模型流程。缺少凭据时继续完成其他功能并明确标记真实调用待验证；不能用假响应冒充真实运行。

故障测试可以使用明确标记的 fake client 返回非法 JSON，验证最多两次和失败日志，不把它计为真实模型成功。实际调用示例、输出和未完成事项写入 `handoff_C.md`，流程与真实日志说明放入 `agent.md`。
