# 2026-10-30 四人初版合并联调

## 结论与范围

四位成员的初版已在 main 合并，正式 Adult 数据规则模式端到端检查通过；A/B/C/D 的 main 交付复验均通过。公共契约 1.0 及其冻结哈希未修改。

真实模型配置缺失，`smoke_check.py --mode llm` 返回 2 / not_ready。受控假模型只用于故障测试，不是实际模型调用或验收。课程报告、PPT 和全员排练仍需另行完成。

## 分支与直接上传 main 的处理

| 来源 | 初版提交 | 处理 |
| --- | --- | --- |
| 原 main | 9ec8077 | 保留全部历史，包含直接上传与修复回退记录 |
| A：member-a-data | d8efee5 | 正常合并；补齐漏传 docs/data.md，移动错放提示词 |
| B：member-b-clean | a140ef5 | 正常合并；与 C 继承的 B 核心代码比对一致，没有重复替换实现 |
| C：member-c-agent | e2efded | 正常合并；保留其 main 直传历史，修复接线与测试边界 |
| D：member-d-ui | a160f15 | 正常合并分类器、页面、CLI、smoke 检查 |

四个成员分支初版提交均已是本地 main 的祖先。未重写、重置或强推历史；未修改各成员远程分支。原工作区 D:/iot/data_agent_course 的未提交内容保留，联调在 D:/iot/integration_20261030 完成。

main 直接上传产生的根目录 `A-20261028-session.md` 和 `usage.json` 与 ai_usage/A 下规范位置的副本逐字节一致；本次删除冗余根目录副本，规范位置及 Git 历史保留。

## 实际修复

1. A 的提示词实际在 ai_usage/A 根目录而账本引用 prompts/；移动原文件，保留 A 原始账本内容。漏传的数据说明由集成人按源码和实际重建结果补齐，并明确注明来源。
2. B 自测读取中文 JSON 未指定编码，在 Windows GBK 环境失败；改为 UTF-8。
3. C 的 RunResult 曾返回拼接后的路径、遗漏页面/验收约定的导出项。现在返回绝对运行目录、相对 artifact 路径，导出前后质量、审计、指标、摘要及全部处理后文件，记录约定的执行事件。
4. 训练/测试来源组交叉在计划或模型调用前拒绝，处理后重新检测质量；异常消息对已知密钥脱敏。运行账本的提示词引用修为项目相对路径。
5. C 的 --integration 曾在检测到真实依赖后仍注入 A/D 替身；现在存在的业务模块必须实际运行。新增来源组交叉提前失败、运行账本相对路径等回归检查。
6. 准备摘要使用 LF，避免 Windows 生成内容触发尾随 CR 检查错误。协作控制回归的临时基线改为显式构造未交付/空账本状态，不再假设主仓库尚无 B 实现。

## 实际验证

| 检查 | 结果 |
| --- | --- |
| 共享契约 / foundation | 通过，冻结契约未变 |
| A --integration | 54 项通过；真实数据和真实 B 规范化 |
| B --integration | 33 项通过；Windows UTF-8 |
| C --integration | 9 个测试通过；真实 A/B/D，模型故障测试明确使用假客户端 |
| D --integration | 分类、15 类非法输入、真实页面/CLI 接线通过 |
| 正式页面 | Streamlit AppTest 通过；3,000 测试行、13 个下载控件；重绘/切换模式不新增运行。这是无界面测试，不声称人工浏览器验收 |
| 完整 rules 集成门禁 | passed；四个角色复验及正式 smoke 全通过 |
| 协作控制回归 | 11 项通过 |
| AI 账本回归 | 9 项通过；四人严格结构检查通过，未知值保留 |
| 真实 LLM | 待验证，配置缺失；没有实际模型请求 |

## 正式运行结果

- 官方原始记录 32,561；参考抽样 10,000；分组划分为训练 7,000、测试 3,000，来源组交叉为零。
- 问题训练集 7,140 条 → 清洗后 7,000 条。测试 3,000 条均保留，标签、来源 ID 和顺序不变。
- Accuracy：0.852333（85.23%）；Macro-F1：0.788846。
- 最终正式运行 ID：`20261030T061637Z-eedd8cfd`。
- 输出：`outputs/integration/integration_rules.json`、`outputs/integration/smoke_rules.json`、`outputs/integration/formal_ui.json`、`outputs/integration/maintainer_revalidation.json`。
- 真实运行目录：`outputs/smoke_runs/20261030T061637Z-eedd8cfd/`，包含处理后 CSV、质量前后报告、计划、审计、混淆矩阵、指标、事件日志和摘要。
- 可提交的脱敏复验摘要在 `evidence/A`、`evidence/B`、`evidence/C`、`evidence/D` 的 `integration_*_20261030.json`；正式原始数据和大部分运行文件另行打包。

## 交接状态的补正方式

B/C 原交接仍是 working，A 的文档/文件缺失导致其旧哈希不可直接复验。先实际运行每人的 `checks/check_X.py --integration`，全部退出 0 且原成员证据文件未变，才新增带 `verified_by: D maintainer integration` 的摘要，并登记新的文件哈希及 ready_for_review 标记。

原 status、last_gate、based_on_commit 保存在各 handoffs/X.json 的 integration_review 中；原成员摘要未覆盖。本次补记不宣称成员曾执行过缺失的 submit 命令，也没有关闭门禁、放宽哈希或用旧报告通过新检查。

## 继续开发

每人先保存并提交自己的修改，再在个人分支运行 `git fetch origin`、`git merge origin/main`。本次没有替队友强制移动个人分支。

完整运行命令见 README。真实模型需在本地设置 LLM_API_URL、LLM_API_KEY、LLM_MODEL，再运行 `python scripts/check_integration.py --mode llm`；不要把密钥提交或贴到聊天里。后续集成修复、正式材料和排练仍需如实记录。
