# 成员 D 交接记录

协作协议：2.0；业务契约：1.0；基线：2325930；分支：member-d-ui。

交付范围为D独立模块；最终ready_for_review以handoffs/D.json的实际门禁为准。main尚未集成，整体课程验收未通过。

最终门禁时发现其他会话并发加入data/README.md、D数据目录说明提示词和账本条目；原工作区因越出本轮D文件清单而被拒绝。所有并发修改原样保留。为避免覆盖或放宽门禁，使用D:/iot/member_d_delivery_20261026独立干净检出，仅复制本轮D文件和基线+本轮两条账本记录重新交付。原目录继续保留数据目录说明的额外记录；该记录未纳入本次提交。最终门禁/完整自测输出在独立检出的outputs/下，原目录也保留本轮较早的实际运行证据。

## 已完成

- src/classifier.py：14固定特征，训练拟合标准化/独热编码/逻辑回归，未知类别、固定矩阵顺序、真实指标与PNG；拒绝残余脏值及来源组交叉，不修改输入。
- app.py：演示数据路径、rules/llm、显式执行、session_state防重绘重复调用、前后统计、策略/理由、审计、指标/矩阵、下载、失败清旧结果、明确标识的合成预览。
- src/cli.py：仅调用C的run_pipeline，正式默认路径、参数与失败退出码；缺C明确提示，已有模块错误不替换。
- scripts/smoke_check.py：只接正式数据和真实模块，缺前置条件返回not_ready；正式成功路径及实际模型日志兼容性仍未验证。
- checks/check_D.py：真实分类、15类输入拒绝、训练参数/特征、AppTest展示/状态、CLI退出码；支持--integration。仅缺C时接线用明确测试替身，D核心不替换。
- 分类说明、验收清单、贡献事实、后续排练脚本、README、集成记录和本轮AI账本。A/B/C、冻结文件、共享样例未改。

## 实际运行与结果

环境为Windows / Python3.12.14，requirements.txt固定的pandas2.3.3、numpy2.3.5、sklearn1.7.2、pydantic2.12.4、streamlit1.51.0、matplotlib3.10.6。

本机系统python指向不可用WindowsApps别名。使用Codex bundled Python创建.venv时ensurepip失败，随后使用bundled pip的--python .venv/Scripts/python.exe安装requirements.txt成功；未改全局环境。以下python均指项目内`.venv\Scripts\python.exe`。

| 命令（项目根目录） | 实际结果 |
| --- | --- |
| python scripts/check_delivery.py --foundation | 退出0，共享基础通过 |
| python scripts/check_contracts.py | 退出0，契约及非法边界通过 |
| python checks/check_workflow.py | 退出0，11项协作控制通过 |
| python checks/check_ai_usage.py | 退出0，9项账本检查通过 |
| python checks/check_D.py | 退出0，fixtures通过；uses_test_doubles=true仅指C接线替身 |
| python checks/check_D.py --integration | 退出2，缺6个上游模块；D分类真实执行，未改摘要 |
| python -m src.cli --help | 退出0 |
| python -m src.cli --train missing-D-check.csv | 自测真实子进程退出1，明确缺输入 |
| python -m src.cli --mode invalid | 自测真实子进程退出2 |
| python -m src.cli --mode rules --train examples/train_small.csv --test examples/test_small.csv | 退出1，明确C的pipeline未交付 |
| python -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false | 实际启动；浏览器检查合成标识、SVG下载及缺C提示；检查后停止服务 |
| python scripts/smoke_check.py --mode rules --report outputs/integration/smoke_rules.json | 退出2，正式文件/上游模块缺失 |
| python scripts/smoke_check.py --mode llm --report outputs/integration/smoke_llm.json | 退出2，同上；未请求模型 |
| python scripts/summarize_ai_usage.py --role D --check --require-records | 退出0，两条真实开发记录结构通过，不代表计费核实 |
| python scripts/summarize_ai_usage.py --check --require-records | 退出1，A/B/C无实际记录，不代填 |
| python scripts/summarize_ai_usage.py | 汇总已登记记录和未知项；outputs/ai_usage/summary.md、summary.json |

真实分类使用人工干净样例训练7行、测试3行：Accuracy=0、Macro-F1=0、混淆矩阵[[0,1],[2,0]]。没有据测试结果改参数。合成预览66.67%是原有示例，不与本次实测混用。

## 证据与声明范围

- fixtures：passed；evidence/D/fixtures.json、evidence/D/browser.json。
- formal_data、real_llm、end_to_end：blocked/待验证；缺正式数据和A/B/C，不是D离线模块顶层blocker。
- 完整输出：outputs/member_D/check.json、integration_check.json、classification/confusion_matrix.png。
- 浏览器：outputs/member_D/browser_check.json、browser_preview.png、browser_missing_pipeline.png。实际下载的合成SVG回收副本为outputs/member_D/browser_download.svg。
- smoke：outputs/integration/smoke_rules.json、smoke_llm.json，均为未就绪证据。
- 最终交付命令：python scripts/check_delivery.py --role D --submit；实际结果由outputs/delivery/D.json及handoffs/D.json的last_gate记录，不手写成功时间/哈希。

## AI账本

保留原条目，新增D-20261026-ui-development，提示词为ai_usage/D/prompts/D-20261026-ui-development.md。本轮可核实成员任务输入1轮；模型标识、内部请求数、token、参数及费用未知，保留null；没有项目真实请求，不把订阅记成0元。未覆盖历史已注明，不改其他成员账本。

## 下一步与未完成

1. A/B/C按本人分支交付；D在main按B→A/D→C正常合并并复验，问题附复现退回原负责人。
2. 按A命令重建正式数据后执行rules集成；C模型配置后执行llm集成，核对artifact键和请求payload，C统一登记逐次真实请求账。
3. 正式≥5000行、四类处理有效性、真实模型/错误修正、正式smoke成功路径、完整页面下载及逐工具进度尚未验证。
4. 报告/PDF、正式PPT、正式数据包、真实成功目录缺失；姓名与展示职责待确认；最终打包/全员排练未执行，详见acceptance.md和demo_script.md。

本文件在最终门禁前编辑，门禁后不改已测文件。当前无A/B/C已交付业务缺陷可退回，评审保留pending，不编造accepted。
