# 发给成员 B 所用 AI 的开工指令

我是成员 B，请在现有项目根目录按协作协议 2.0 开发规范化与清洗，不重建项目。

先读取 AGENTS.md、README.md、docs/START_HERE.md、docs/低沟通协作协议.md、collaboration/roles.json 的 B 条目、docs/公共接口说明.md、src/schema.py、src/contracts.py、docs/成员B_AI任务.md，以及本人的交接和集成退回记录。

使用 member-b-clean 分支，只主要修改 B 归属的文件。优先交 normalize_frame；使用现有脏样例、规则计划、清洗参考数据和状态，不等待 A 正式数据或 C 模型。不私改冻结契约，不修改共享样例迎合实现。

实现并实际运行 checks/check_B.py（需支持 --integration），填写 docs/handoff_B.md、handoffs/B.json，再执行 python scripts/check_delivery.py --role B --submit。检查通过后按仓库协作规则提交个人分支。最终给出变更、命令、实际结果、未验证项及下一步。

若你不能读取工作区，请先列出缺少的上述文件；若不能执行代码，输出文件内容和待执行命令，并把运行结果保留 not_run，不能声称已通过。角色和文件已明确时，不重复追问普通实现选择。

使用 AI 开发或制作材料时，先读 docs/AI使用记录规范.md，维护 ai_usage/B/usage.json 和 ai_usage/B/prompts/ 中的实际提示词。每段会话更新原记录，换模型或新会话另建条目；只填可核实的模型、参数、请求数、token 和费用，未知用 null，聊天轮次另记，不能将订阅使用记为 0 元。交接前核对账本，至少有一条真实记录。
