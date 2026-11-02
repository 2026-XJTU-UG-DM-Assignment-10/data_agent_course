# DeepSeek真实模型补验（2026-11-02）

正式数据的模型模式完整验收已通过。此说明补充现有规则阶段PDF/PPT；它不改变旧运行和旧截图的模式或日期。

| 验证 | 实际结果 |
| --- | --- |
| 官方API与模型 | https://api.deepseek.com，deepseek-flash；models端点实际200 |
| C正式入口 | `checks/check_C.py --integration --real-llm --report outputs/real_llm_check/deepseek_C_20261102.json`退出0；20261102T031150Z-ef13473e，一次请求、记账核对通过 |
| main首次完整门禁 | 20261102T031210Z-102c7ebc的业务pipeline成功；D事件解析误报ValidationError，门禁退出2，失败报告保留 |
| D修复 | c00ea29；只剥离C事件attempt元数据，再严格校验LLMReply；正例、8类拒绝及rules边界回归通过 |
| main最终完整门禁 | main 1128a52执行`check_integration.py --mode llm`退出0；四角色passed，20261102T031942Z-8d6dc4ee，正式数据与真实模型证据passed |

实际训练7140→7000行、测试3000行，缺失/重复/范围异常/格式问题处理后均为0。模型选择median、constant与Unknown；Accuracy为0.8523333333333334、Macro-F1为0.788845681782975、混淆矩阵为[[2101,189],[254,456]]，与规则模式相同。两次模式采用相同策略与固定种子，不把相同成绩解释为模型带来的提升。

3次外部模型请求均成功、每次一条C项目运行记录：

| source_id | 输入token | 输出token |
| --- | ---: | ---: |
| 20261102T031150Z-ef13473e:1 | 714 | 418 |
| 20261102T031210Z-102c7ebc:1 | 714 | 369 |
| 20261102T031942Z-8d6dc4ee:1 | 714 | 359 |
| 已知合计 | 2142 | 1146 |

token取自API返回，费用未提供，C账本保留unknown/null。temperature=0是实际请求字段；客户端没有显式设置thinking模式或max_tokens，不推断供应商的隐含参数，也不将聊天轮次计为模型请求。三次请求均首次返回合法计划，没有实际触发纠错；两次修正上限及失败记账由受控测试覆盖。

API Key仅由本地临时进程环境加载，未写入配置文件，退出后清理；新的终端或页面进程仍需设置LLM_API_URL、LLM_API_KEY、LLM_MODEL。项目不会自动加载.env。当前官方接口及模型标识参考[首次调用](https://api-docs.deepseek.com/)和[模型列表](https://api-docs.deepseek.com/api/list-models/)，以本次models实际响应为核对依据。

完整证据：evidence/C/real_llm_deepseek_20261102.json、evidence/C/main_llm_20261102.json、evidence/D/main_llm_20261102.json；原始日志、失败报告和完整运行在outputs/real_llm_check及outputs/smoke_runs。新的技术验证包为outputs/real_llm_check/data_agent_course_llm_verified_20261102.zip，包含源码、数据、旧规则主运行、三次真实模型运行、材料和AI账本/汇总；llm_package_check.json记录解压和SHA-256结果。

未执行：真人跨机复现、全员排练、原生PowerPoint人工交互、LLM页面人工点击/录屏、真实服务故障纠错。姓名/口头分工及B对正式案例文字的确认仍待。当前备份是成功运行与日志，不称录屏；PDF/PPT中的原页面截图仍为rules。
