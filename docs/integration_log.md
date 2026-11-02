# 集成检查与退回记录

## 最新：2026-11-02公网HTTPS入口与后台服务

按用户授权配置https://111.230.149.166/：官方Caddy2.11.7+公信IP证书、独立demo账号bcrypt认证，Streamlit继续仅127.0.0.1:8501。CourseAgentGateway/CourseAgentApp自动启动，分别LocalService/NetworkService低权限账号；key用Windows DPAPI加密并限ACL，不进源码/日志/证据包。服务实际重启通过，关闭SSH终端与隧道后公网14项HTTP/认证/TLS/WSS检查及真实PNG下载/哈希仍通过。

通过同一新服务的回环网页实际点击一次llm处理：20261102T100936Z-a2090032成功，7140→6998/3000，median/most_frequent，Accuracy0.8523333333、Macro-F1 0.7872823666。新增真实DeepSeek1次，1262输入/1365输出token、费用未知；C自动业务记录原样追加，旧记录逐字段一致。项目累计6次、5928输入/5652输出token。本轮聊天不记录开发prompt，认证/网络测试不冒充模型请求。

26项原始包解压/逐项哈希通过，包含新运行和服务快照，排除所有私钥、模型加密blob和网页登录凭据/哈希配置。部署、实际故障修复及范围见docs/public_gateway_20261102.md和evidence/D/public_gateway_20261102.json。原有Windows镜像MpsSvc已停用，未改变全局状态；云端此前全部TCP规则仍需操作者收紧。未实际整机重启、手机/教室网络或全员排练，未更改业务模块与冻结契约。

收口检查：foundation与16条AI账本结构检查退出0，公开新增文本未发现凭据形态值，git diff --check通过。提交前远端仍为4c6fcaf，本次不包含其他成员改动或任何网页登录秘密。

## 最新：2026-11-02独立云服务器复现

周锦晨（D）完成服务器首次登录及SSH/云防火墙接入，AI在独立Windows Server 2022（2CPU/2GB）新建Python3.12.10环境。Git bundle、官方安装包/PyPI wheel和官方Adult原始文件55项传输哈希一致；独立安装依赖、pip check、重新生成正式数据，12条环境/业务命令最终退出码均0。验证main d5d5787，业务源码及冻结契约未改。

rules与真实llm完整门禁均退出0、四角色passed。rules：20261102T084136Z-d398f7b5，7140→7000/3000，Accuracy0.8523333333、Macro-F1 0.7888456818；llm：20261102T084237Z-decc1cbf，median/most_frequent，填补后再去重2行，7140→6998/3000，Accuracy0.8523333333、Macro-F1 0.7872823666。不能套用旧LLM的7000行或指标，也不宣称模型提升分类。

新增真实DeepSeek请求1次成功，无纠错/重试，输入1262/输出1418 token、费用未知。C生产账本及对应业务提示词原样带回，仅追加该条，不改旧记录或新增C开发会话；本轮聊天prompt按用户要求不记录。账本结构检查15条通过，本机C受控16项复验通过，不算额外API请求。

交付复核：foundation退出0，C与D的main integration角色复验均退出0，D新增服务器收据通过门禁读取；未重新发起模型请求。最后检查远端main仍为d5d5787，没有覆盖并发新推送或原工作区修改。

服务器网页经仅本机SSH隧道访问，实际加载LLM历史成功运行、列质量/分布、填补值/理由、指标/矩阵及13下载入口。CSV/events/summary三份浏览器下载逐字节一致，其余10项由smoke验证，不称已逐项浏览器下载。原始证据包61文件逐一哈希与解压校验通过；详见docs/server_reproduction_20261102.md、evidence/D/server_reproduction_20261102.json和outputs/server_reproduction_20261102/package_check.json。独立服务器验收已完成；原生PowerPoint、排练/录屏、课堂网络与B案例文字确认仍待，不将本次技术操作写成小组排练。

## 最新：2026-11-02正式PDF/PPT收口

D材料提交e5e0eee通过submit，正常合入main 08c9b07后check_integration.py --mode rules实际退出0、四角色passed。本阶段未改业务模块、冻结契约或C账本，未新发API请求；最后真实LLM验证仍为8968c65对应的20261102T043037Z-b0fc7c1a。新的6页报告与7页PPT统一该模型运行、规则对照20261102T042950Z-969fddba、四项功能、姓名及D代完成部分，不写分类提升。

PDF与PPT全部逐页渲染目视检查，PPT导入保留原稿按锚点编辑，继承原尺寸/字体/设计。发现过路径替换图片未实际嵌入，改用真实字节嵌入；现2张媒体与原始证据哈希完全一致。3张原生表格、字体与重新导入检查通过。原生PowerPoint应用访问授权等待超时，未记为通过；无录屏或真人跨机/排练声明。证据evidence/D/materials_20261102.json和materials_main_rules_20261102.json，原始验证在outputs/materials_20261102。

原始规则材料副本和旧交付包保留。新包outputs/real_llm_check/data_agent_course_materials_20261102.zip包含源码、数据、全部真实请求/成功运行、受控故障、正式材料及AI记录；实际解压/SHA-256校验见同目录materials_package_check.json。D当前同一会话条目更新为2次可核实成员输入，内部用量仍未知；不补录此前被排除的对话。剩余真人事项见acceptance.md和demo_script.md。

## 最新：2026-11-02四项功能补全完成

按用户本次要求，D补训练分布统计、列级质量图、成功历史回放和固定结构CSV上传/预检，并恢复本次prompt使用登记。A统计扩展f055a31、C训练摘要与共享系统提示词89a6eb4、D页面与回归e6a15ad均按本人分支实际submit退出0，正常合并。main 8968c65的rules/LLM完整门禁实际退出0、四角色passed；当前代码的A60项断言、B33项断言、C16项测试、D16项新增拒绝与正例/AppTest全部通过。冻结契约和B核心未改，其他工作区未提交修改保留。

LLM运行20261102T043037Z-b0fc7c1a，一次真实请求。模型理由明确引用capital_gain偏度11.4218、capital_loss偏度4.4913及列缺失率，实际选择仍为median/Unknown，Accuracy0.8523333333、Macro-F1 0.7888456818。此结果证明提供并使用统计依据，不证明策略变化或分类提升。C运行账新增输入1262/输出1723 token，成本未知；C按分支门禁补交真实运行增量，不与D开发账重复。

浏览器AI操作实际完成正式本地CSV/双文件上传规则运行、14列图与分布、历史标识检查；新证据evidence/D/adaptive_features_20261102.json及evidence/D/adaptive_main_20261102.json。预检/回放没有新增项目模型请求；原始ID与模式保留。历史包可重定位，损坏/越界记录拒绝，小样本与≥5000规模明确标识。应用预检20 MB限制与框架200 MB接收上限分别说明。

新功能说明docs/report_adaptive_features_20261102.md，新技术包data_agent_course_adaptive_20261102.zip及实际解压哈希记录在outputs/real_llm_check；旧包不覆盖。D-20261102-adaptive-features只记录本次用户授权和补全内容，不补录此前被排除的对话。PDF/PPT整体同步、原生PowerPoint、真人跨机、全员排练及LLM页面录屏仍待；本轮没有录屏或新增任意CSV/逐列混合策略。

## 最新：2026-11-02 DeepSeek真实模型验收

真实API使用官方地址https://api.deepseek.com，models端点返回200及deepseek-flash/deepseek-v4-pro；实际采用deepseek-flash。C真实入口退出0，运行20261102T031150Z-ef13473e；随后main运行20261102T031210Z-102c7ebc业务pipeline也成功，但D的verify_events把事件attempt元数据传入严格LLMReply，出现extra_forbidden，完整门禁退出2。这一失败不是鉴权/模型/清洗失败，原始失败报告及实际请求账本保留。

D修复c00ea29仅剥离已知attempt事件元数据，未放宽其他响应字段或冻结契约；新增合法事件/8类拒绝边界及rules无请求回归，D submit退出0，既有两份真实日志重放通过。修复正常合入main 1128a52后，完整check_integration.py --mode llm实际退出0，A/B/C/D全部passed，最终run_id为20261102T031942Z-8d6dc4ee，formal_data_checked/real_llm_checked均true。C交接和逐次账本按C分支实际门禁补交，证据evidence/C/main_llm_20261102.json；D接收证据evidence/D/main_llm_20261102.json。后续只更新文档、账本和归档，不把这些变更冒称又发起模型请求。

3次真实请求均在C账本calls=1/result=succeeded，对应输出目录和事件；合计输入token2142、输出token1146。服务未返回可核实费用，保持null；开发账本不追加配置指导对话。两种模式结果相同源于本次模型同选median与Unknown，不能据此声称模型改善指标。主运行训练7140→7000/测试3000，Accuracy0.8523333333、Macro-F1 0.7888456818。

密钥只通过临时进程环境提供，未持久化，已核对源码和运行证据不含该密钥。模型业务prompt由pipeline正常保存；所有真实记录与完整运行备份在新的LLM技术验证包，旧规则包不覆盖。正式PDF/PPT仍为准确标明日期的规则阶段材料，真实模型结果另附docs/report_llm_validation_20261102.md。真人跨机、全员排练、原生PowerPoint、真实LLM页面人工操作/录屏、真实服务纠错和B文字确认未验证，不用自动检查替代。

## 最新：2026-11-02推送复核与授权代完成

本轮fetch发现A分支新增d7cc1da，B/C/D无新推送。A经差异/交接评审和54项实际复验后，正常合入main（13d35de）。A已确认先前D补写的数据说明；D用实际CSV、profiler和共享规范化独立重算853格原生缺失、3行原生重复、复制额外105格缺失及20格格式问题，均一致。A_count_review.json保留重算结果。

C真实验收旧入口直接调用agent，绕过pipeline的逐次运行账本。按用户明确授权“假如c未完成它的一部分，则由我代替完成”，D在member-c-agent完成18c1d68，实际C submit退出0，正常合入main（2a802c8）。新入口使用正式数据和生产pipeline并核对每次尝试的C运行账；客户端补充usage/model响应和超时边界。15项测试通过，远程HTTP是明确替身，账本隔离到临时目录；没有将这些计作外部模型调用。开发使用记入D本轮账本，保留原C开发记录。

D增量提交98de1aa的submit实际退出0，正常合入main 565ab0d。2026-11-02在该main实际运行check_integration.py --mode rules退出0，A/B/C/D复验全部passed；A54项、B33项、C15项，D真实分类/页面/CLI自测和正式smoke通过。新证据evidence/D/main_rules_review_20261102.json，原始日志outputs/review_20261102/main_rules_gate.log。冻结契约及哈希文件未改，其他两个工作区未提交修改保留。

正式新smoke仍为7140→7000训练、3000测试，Accuracy0.8523333333、Macro-F1 0.7888456818。报告/PPT保留原浏览器主运行20261030T070819Z-7779c942的准确日期，本轮只更新A确认、计数解释和C代完成事实；PDF6页/PPT7页已全部渲染检查，PPT结构、字体、3张原生表格和重导入检查零发现。四人AI账本共9条开发记录结构检查通过，未知请求/token/费用保持null，无真实project_runtime记录。

用户确认“尚无配置，先完成代码、测试和材料”。实际checks/check_C.py --integration --real-llm预检退出2，real_request=false；未执行缺配置的main完整llm集成。配置后先运行该真实入口，再在main运行check_integration.py --mode llm，核对C逐次账本和运行证据。规则/受控范围无待退回代码缺陷；B正式案例文字确认仍待。真实模型成功/备份录屏、原生PowerPoint人工交互、另一位真人跨机复现、全员排练、姓名与口头分工仍未验证。

本轮阶段包位于outputs/review_20261102/data_agent_course_rules_stage_20261102.zip，包含源码、正式数据、主运行和新smoke输出、材料、AI记录及本轮检查；实际解压和SHA-256结果以同目录package_check.json为准。旧10月30日包和历史证据不覆盖。

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
