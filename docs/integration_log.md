# 集成检查与退回记录

## 最新：2026-10-30第二阶段规则交付

member-d-ui提交e9718f8已由D正常合入main；本机检出D:/iot/member_d_delivery_20261026，保留其他两个工作区未提交修改。实际执行check_integration.py --mode rules退出0，A/B/C/D复验均passed。新证据evidence/D/main_rules_stage2_20261030.json；原始报告outputs/integration/integration_rules.json。这是规则范围接受，真实模型及真人事项仍待补。

| 角色/范围 | 本轮状态 | 依据/下一步 |
| --- | --- | --- |
| A 数据/检测 | accepted（rules） | main真实依赖复验；确认集成人补写数据说明。三个生成清单归属已精确修复 |
| B 清洗 | accepted（rules） | main真实复验；D从正式运行提取案例，待B复核文字 |
| C 流程/日志 | accepted（rules），真实LLM待验 | 9项真实依赖自测；受控非法计划两次后拒绝，非实际模型请求 |
| D 分类/页面/材料 | accepted（当前规则范围） | D submit退出0、main复验0，人工页面/下载和6页报告/7页PPT已检查 |

报告、PPT和人工截图主运行统一为20261030T070819Z-7779c942：7140→7000训练、3000测试，Accuracy0.8523333333、Macro-F1 0.7888456818。完整main smoke会生成自己的唯一运行ID，见新增摘要，不覆盖材料主运行。缺失5815、重复140、异常70、格式1218在训练复查清零；各计数可重叠。

实际浏览器打开127.0.0.1:8503，执行一次正式rules；13下载控件可见，CSV/events/summary下载内容与主运行文件逐字节一致。选择llm保留rules旧结果及run_id、不新增运行；缺输入时清除旧指标。evidence/D/formal_browser_stage2_20261030.json记录范围，路径穿越由既有D自测覆盖，不谎称在浏览器做过恶意输入测试。

A清单问题在隔离检出真实prepare_data后复现：tracked准备摘要generated_at变化触发归属门禁2。只为A补三个精确manifest路径，真实A门禁变0；12项工作流回归验证其他路径/角色仍拒绝。冻结契约及哈希不变，其他业务/账本未修改。

真实模型缺LLM_API_URL/LLM_API_KEY/LLM_MODEL，用户明确要求先完成规则和材料；一次LLM预检返回2，无实际请求，未执行新的main LLM完整验收。outputs/final_delivery/controlled_fault.json为真实agent配明确TEST_DOUBLE的受控失败，假调用2次，不写项目运行账。

规则阶段包outputs/final_delivery/data_agent_course_rules_stage_20261030.zip含源码、正式/处理后数据、主运行、受控错误证据、材料与四人AI账本/汇总。package_check.json记录解压和哈希检查；包不是全部课程终验。PDF6页/PPT7页逐页渲染并重新打开解析通过，原生PowerPoint交互仍not_run。真实模型成功/备份录屏、跨机真人复现、全员实际排练、姓名和口头分工未确认；见acceptance/demo_script。

## 历史记录（以下保留原时间点状态）

## 2026-10-30 初版合并联调（当前状态）

完整结论、提交来源、修复、真实指标和验证限制见 [本次联调报告](integration_20261030.md)。

| 角色 | 当前评审状态 | 范围 |
| --- | --- | --- |
| A | accepted | 正式数据准备、质量检测；54 项真实依赖复验 |
| B | accepted | 规范化、训练清洗、测试转换；33 项复验 |
| C | accepted（规则范围） | 计划/流程/导出；9 项测试、正式规则流程通过；真实模型待配置 |
| D | accepted（规则范围） | 分类、页面、CLI、完整 rules 门禁及正式页面 AppTest 通过 |

本次规则模式整体验收通过；真实模型、最终报告/PPT和全员排练仍待完成。下面保留历史记录，历史的“未交付”不代表当前状态。

---


由 D 维护。第 4/6/8 天是技术检查节点，默认由 D 异步执行，无需四人同时在线。模块问题由原负责人修复；D 负责接线、定位和最终验证。

| 角色 | 当前评审状态 | 证据/提交 | 需修复的问题 | 下一步 |
| --- | --- | --- | --- | --- |
| A | pending | 尚未交付 | — | 等待数据与检测交付 |
| B | pending | 尚未交付 | — | 等待清洗交付 |
| C | pending | 尚未交付 | — | 等待规则/模型流程交付 |
| D | pending | 本次独立模块自测通过，交付门禁生成 handoffs/D.json；evidence/D/fixtures.json | 真实依赖尚缺，不能标记完整集成 accepted | 保留 member-d-ui 交付，待 A/B/C 就绪后在 main 正常合并与复验 |

状态使用 `pending、accepted、changes_requested`。退回问题写清角色、最小输入、复现命令、实际错误、预期结果，不要求全员开会。不要把“待评审”自动当作已接受。

## 2026-10-26 D 独立开发与集成前检查

- 开工时 main / 工作区干净，四个成员分支同为 2325930。实际 git fetch origin 后仍无其他交付；已切 member-d-ui，仅改 D 归属文件，保留 A/B/C 和冻结契约。
- D 分类真实训练7行人工样例、测试3行；Accuracy=0、Macro-F1=0、矩阵 [[0,1],[2,0]]。通过未知类别、训练拟合边界、排除标签/ID、15类输入拒绝。不是正式实验。
- AppTest 和 CLI 成功/失败检查通过；仅缺失的 C 接线被明确替身替代。实际浏览器检查合成标识、示例SVG下载和真实入口缺C错误。合成预览指标不作为实测。
- checks/check_D.py --integration 返回2，uses_test_doubles=false；D分类真实执行，但缺6个上游模块，未执行成功接线；outputs/member_D/integration_check.json，未改 evidence。
- scripts/smoke_check.py 的 rules/llm 均返回2 / not_ready；outputs/integration/smoke_rules.json、smoke_llm.json。缺正式7个文件及6个上游模块，没有实际端到端或模型请求。
- 当前未合并 main；四模块未齐备，scripts/check_integration.py --mode rules/llm 的正式 main 集成尚未执行。不将 member-d-ui 自测称为 main 集成通过。后续按 B→A/D→C 正常合并与复验。
- AI全员严格检查实际失败（A先报无记录，汇总显示A/B/C均空）；D单人严格检查通过，不改他人账本。outputs/ai_usage 两份汇总仅统计已登记记录与未知项。
- 公共契约、11项协作控制与9项AI账本回归实际通过。首次AppTest退出出现Windows沙箱临时目录清理错误，限定到outputs/member_D/tmp后重跑已消除；bare-mode提示仍为测试环境提示。

### 等待交付与最小复现

A/B/C均未声明交付，没有已提交业务缺陷可退回，评审保持pending。以下是缺失依赖，不伪装成他人实现错误。命令中的 python 在本机使用 .venv/Scripts/python.exe。

| 归属 | 最小复现 | 实际结果 | 下一步 |
| --- | --- | --- | --- |
| A | python scripts/smoke_check.py --mode rules --report outputs/integration/smoke_rules.json | 缺正式数据、manifest及profiler | 交付prepare_data/profiler，按--seed 42 --sample-size 10000重建 |
| B | python checks/check_D.py --integration | missing_dependencies含normalization/cleaner，退出2 | 完成规范化、清洗、测试转换和本人自测 |
| C | python -m src.cli --mode rules --train examples/train_small.csv --test examples/test_small.csv | 明确Member C has not delivered src/pipeline.py，退出1；浏览器同样提示 | 交付真实规则流程，再接模型/日志，不静默用替身 |
| C | python scripts/smoke_check.py --mode llm --report outputs/integration/smoke_llm.json | not_ready，未调用模型 | 模块/正式数据齐备后配置并实测；真实请求账只由C登记 |

正式材料缺项见docs/acceptance.md；本次未生成报告PDF、正式PPT、正式数据包或真实成功目录，未完成全员排练。docs/demo_script.md是后续安排脚本，不是排练证明。

### 并发修改隔离

首次D提交门禁发现本轮期间其他会话新增data/README.md和D数据目录说明记录，按归属检查返回not_ready。未重置、覆盖、暂存或提交这些其他会话修改，也未放宽roles.json。使用D:/iot/member_d_delivery_20261026本地干净检出，仅复制本轮D交付文件及基线+本轮账本进行最终门禁；原工作区和并发新增记录保留。交付快照的D账本为2条，原工作区另含目录说明会话记录，二者覆盖范围不同。

## 课程最终验收

- [ ] 四个模块均经过实际评审。
- [ ] 正式数据规模、来源和四类质量问题核对通过。
- [ ] 规则模式完整运行，使用真实业务模块。
- [ ] 真实模型完整运行，证据日志保留，调用成本如实记录。
- [ ] 四人的开发 AI 账本、提示词和 C 的项目请求记录齐备；D 已汇总，实际/估算、币种及未知项分别列明，无重复统计。
- [ ] 数据边界、故障处理、输出文件和页面检查通过。
- [ ] 报告、源码、数据、PPT、贡献说明和日志齐全。
- [ ] 换组员或新环境按 README 复现，完成一次全员排练。
