# 成员 D 交接记录

## 当前：四项功能补全（2026-11-02）

本次用户明确要求补齐四项中低成本功能并登记prompt。D在成员归属分支补A的合法数值分布统计（6项新增检查）和C的训练缺失率/模型依据提示（新增1项测试），各自submit实际通过并正常合入main；D开发使用统一记入D-20261102-adaptive-features，不补录此前被排除的对话。

D页面新增：固定17字段CSV上传和无模型预检，UTF8-BOM/GB18030、逗号/分号/制表符和字段顺序兼容；标签/来源组与ID交叉、无有效训练数值、重复头/坏行/字段错误/大小拒绝。内容哈希目录保存标准UTF8，页面仍只调用C的pipeline。14列缺失率图、训练分布与实际填补值可查；20%提示仅供展示，不改变处理规则。回放校验完整文件/日志/模式与路径，重定位归档目录，优先显示≥5000规模并标识小样本；回放/重绘/预检不触发模型。

实际D自测含上传字节→正式生产rules流程、16项拒绝、编码/字段顺序、输入不变、历史路径/搬迁/缺文件/不执行、实际列统计，以及AppTest的上传空输入、回放与模式切换。浏览器实际执行正式rules、上传正式两文件、检查列级图及回放。最终D submit、main rules/LLM新复验和模型实际选择以输出及integration_log新增记录为准；旧成绩不冒充本轮新模型结果。

说明docs/report_adaptive_features_20261102.md，证据outputs/adaptive_20261102及evidence/D/adaptive_features_20261102.json。报告/PPT原规则快照和既有真实模型补验保留，正式PDF/PPT整体更新、原生PowerPoint/真人跨机/全员排练仍为单独待办；本轮没有录屏。未改冻结契约或B核心。

## 真实模型联调补充（2026-11-02）

DeepSeek官方接口/模型deepseek-flash已配置到临时进程并实际调用，C正式验证退出0（20261102T031150Z-ef13473e，一次请求，账本核对通过）。第二次main运行的业务pipeline也成功，但D smoke把C响应事件的attempt元数据传给严格LLMReply，误报ValidationError。真实数据、模型及C记账没有因此失败；初次完整main门禁退出2的原始报告保存在outputs/real_llm_check/deepseek_main_initial_failure_20261102.json。

本次在member-d-ui修复D解析器，仅剥离已知事件元数据attempt，保留LLMReply字段校验。新增合成事件回归：合法C事件、非法usage/额外响应字段、缺模型/提示词、测试替身标识、序列/运行ID/请求预算、无请求rules边界。它们不发送外部请求；另用两次既有真实日志实际重放解析。本轮不改冻结契约。D submit后正常合入main，再用真实配置执行完整LLM门禁；最终结果看integration_log和新增证据，不预填通过。

业务模型的实际prompt与逐次请求由pipeline保存；本轮配置指导对话不登记开发prompt使用。密钥未持久化，新进程仍需本地加载。历史材料是规则阶段快照，真实模型补验结果单独提供；真人跨机、原生PowerPoint及全员排练仍待。

## 当前增量（2026-11-02）

在D:/iot/member_d_delivery_20261026继续，原两个工作区的未提交修改原样保留。接收A最新推送d7cc1da并正常合入main，A实际复验54项通过；独立重算A说明的853格原生缺失、3行原生重复、复制额外105格缺失和20格格式问题均一致。A数据说明已确认，B正式案例文字确认仍待。

用户授权D代完成C未尽部分，且明确“尚无配置，先完成代码、测试和材料”。在member-c-agent、main 13d35de基础上补真实验收入口：通过正式数据/生产pipeline逐次记账，拒绝非法HTTP响应usage及非有限超时；15项受控测试和C submit实际退出0，提交18c1d68、正常合入main 2a802c8并推送。真实配置预检实际退出2、real_request=false；受控HTTP账本位于隔离临时目录，未写入C项目账本。开发会话记入D-20261102-review-and-C-delegation，未代填C人工开发记录。

正式rules复测run_id为20261102T024227Z-478068af，7140→7000训练、3000测试，Accuracy0.8523333333、Macro-F1 0.7888456818，与旧主运行一致。outputs/review_20261102/rules.json及evidence/D/latest_review_20261102.json记录实际结果。报告与PPT仍使用20261030T070819Z-7779c942对应的真实浏览器截图，并明确原日期；本轮更新A确认/计数解释和C代完成事实。PDF6页、PPT7页全部渲染检查，PPT结构/字体/3张原生表格/重导入校验通过。

本轮D submit及合并后main规则门禁以实际生成的last_gate、outputs/delivery/D.json、outputs/integration/integration_rules.json和integration_log新增记录为准；本文件定稿后执行，不预填成功。新包位于outputs/review_20261102/，旧包不覆盖。

未验证项：真实模型完整流程及成功备份/录屏；原生PowerPoint人工交互；另一位真人跨机复现、全员实际排练、姓名与口头分工；B对正式案例文字的确认。凭据由外部提供，配置后用checks/check_C.py --integration --real-llm并在main执行llm集成。当前代码/规则/阶段材料范围可独立交付。

## 当前交付（2026-10-30第二阶段，基于main fc7103c）

四模块已在main集成，旧的缺上游描述仅为2026-10-26历史。本轮在干净member-d-ui检出同步origin/main继续，未改原D:/iot/data_agent_course和D:/iot/integration_20261030的未提交工作。

本次新增：A三个被跟踪生成清单的精确归属修复及12项工作流回归；正式数据规则复验；真实浏览器执行、策略/质量/指标/13下载控件及三类文件内容核对；6页报告MD/PDF、7页PPTX/提纲/讲者备注、贡献/演示/跨机排练步骤和规则阶段包。分类、清洗、检测、总流程复用main有效实现，未改冻结契约或其他成员业务/账本。

主运行20261030T070819Z-7779c942（rules），7140→7000训练/3000测试，Accuracy85.23%、Macro-F1 0.7888456818。质量缺失5815、重复140、异常70、格式1218均归零。报告截图与日志同run_id；补充正式smoke输出outputs/final_delivery/rules.json。

实际命令（python为D:/iot/data_agent_course/.venv/Scripts/python.exe）：

- scripts/check_delivery.py --foundation：0。
- scripts/smoke_check.py --mode rules --report outputs/final_delivery/rules.json：0，真实模块和正式数据。
- checks/check_workflow.py：0，12项；隔离真实prepare_data复现A门禁修复前2、修复后0。
- checks/check_D.py --integration和最终--role D --submit：以最终outputs/delivery/D.json及last_gate为准，定稿后实际执行。
- 浏览器streamlit run app.py --server.address 127.0.0.1 --server.port 8503：实际执行一次正式rules，三份下载与输出逐字节相同，关闭服务；outputs/final_delivery/browser_check.json。
- PDF6页逐页渲染检查；PPT7页导出/重导入/结构/字体/原生表格与逐页渲染检查通过。原生PowerPoint交互未做，Codex打开请求为queued，不称为已在PowerPoint验收。

本轮开发记录D-20261030-final-delivery，提示词ai_usage/D/prompts/D-20261030-final-delivery.md；用户明确回复“尚未配置，先完成规则验证和材料”。内部模型版本/次数/token/费用未知。未发送真实项目模型请求，未改C账本。

真实模型、真实模型成功备份/录屏、另一位真人跨机复现、姓名/口头分工确认和实际全员排练仍待补。docs/acceptance.md列明缺项；规则阶段包不称为课程全部最终包。集成接收与复验在main正常合并后记录到docs/integration_log.md，具体执行结果以新增证据为准，保留早前快照。

## 初版历史记录（2026-10-26，原文保留）

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


## 2026-10-30 main 集成复验补记（D）

保留上述成员原始记录；本次用户授权合并初版，由 D 在 main 使用真实依赖复验。具体改动、提交来源、验证边界和证据见 `docs/integration_20261030.md`。新的 handoffs JSON 复验标记由集成人登记，不代表成员此前执行过缺失的 submit 命令。真实模型凭据缺失，LLM 验收仍待完成。
