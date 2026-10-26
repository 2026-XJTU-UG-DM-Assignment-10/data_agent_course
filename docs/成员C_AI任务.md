# 成员 C：可直接交给 AI 的任务

从 `docs/START_HERE.md` 进入，先读协作协议 2.0、`collaboration/roles.json` 的 C 条目和公共契约 1.0，再实施智能体、模型适配和总流程。读取本人交接和 D 的退回记录，继续未完成项，不依赖聊天历史。可直接复制的开工词见 `prompts/C.md`。

## 我负责的文件

- `src/llm_client.py`
- `src/agent.py`
- `src/pipeline.py`
- `docs/agent.md`
- `docs/handoff_C.md`
- `handoffs/C.json`、`checks/check_C.py`、`examples/role_C/` 中本人新增测试样例。

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

第 4 天目标为真实模块的规则流程，第 6 天目标为真实模型流程，由 D 异步检查，不要求全员在线。先使用 `quality_report_example.json、llm_reply_example.json、run_result_example.json` 开发，不等待 A/B/D；缺失同伴依赖可以在自测中使用替身，正式流程不能静默使用替身。缺少凭据时继续其他功能并明确标记真实调用待验证。

故障测试可以使用明确标记的 fake client 返回非法 JSON，验证最多两次和失败日志，不把它计为真实模型成功。实际调用示例、输出和未完成事项写入 `handoff_C.md`，流程与真实日志说明放入 `agent.md`。

## 固定自测和交付

实现 `checks/check_C.py`：默认离线执行规则、白名单、测试摘要拒绝、最多两次请求、错误记录和管道接线检查；支持 `--integration`，管道接线时强制真实的 A/B/D 模块。故障单测的假模型可以继续使用，但必须标注。

另支持 `--real-llm --report PATH`，在凭据配置后显式执行一次真实模型验证并保存证据。默认自测不发送真实网络请求。

填写 fixtures、real_llm 等各自状态，执行 `python scripts/check_delivery.py --role C --submit`。离线模块可先待评审，缺少真实凭据记在 real_llm 和 next_action；如果它不阻止离线交付，不设为整份模块的顶层 blocker。课程最终验收仍必须补真实调用证据。

原始请求与响应留在 outputs；随代码提交 `evidence/C/` 中的脱敏验证摘要，让交接 JSON 引用这些摘要。默认自测可用明确标记的假客户端，真实模型摘要必须对应实际请求，不能包含密钥或完整提示词/返回文本。

## 本人 AI 使用记录

按 [AI 使用记录规范](AI使用记录规范.md)维护 `ai_usage/C/usage.json` 和本人提示词文件，每段实际开发会话及时更新，交接前核对模型、参数、次数、费用和未知项。不要修改其他人的账本，也不要用开发辅助记录替代项目实际运行证据。

项目每次真实请求（含失败及修正）另建 project_runtime 条目，calls=1，source_id 使用原始 events 的 run_id:请求序号；提示词及原始事件可追溯。D 触发的项目运行也由 C 统一登记，不重复计账。
