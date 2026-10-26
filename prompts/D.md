# 发给成员 D 所用 AI 的开工指令

我是成员 D，请在现有项目根目录按协作协议 2.0 开发分类、页面、CLI，并负责异步集成，不重建项目。

先读取 AGENTS.md、README.md、docs/START_HERE.md、docs/低沟通协作协议.md、collaboration/roles.json 的 D 条目、docs/公共接口说明.md、src/schema.py、src/contracts.py、docs/成员D_AI任务.md，以及四份交接与 docs/integration_log.md。

使用 member-d-ui 分支实现本人功能；用共享干净样例和示例页面结果先开发，不等待 B/C。只主要修改 D 归属文件，不替其他成员重写模块，不私改冻结契约。集成阶段在 main 进行正常合并和检查。

实现并实际运行 checks/check_D.py（需支持 --integration），填写 docs/handoff_D.md、handoffs/D.json，再执行 python scripts/check_delivery.py --role D --submit。其他成员的修改按交付记录异步评审；问题附复现步骤退回文件归属人。

四模块齐备后运行 python scripts/check_integration.py --mode rules，再用真实模型配置运行 --mode llm；将结果与证据写入集成记录。最终检查正式材料并组织一次排练。缺少实现或证据时保留待验证，不补空函数或伪造成功。

若不能执行代码，输出待执行命令，不能写已通过。最终给出实际集成状态、退回事项、运行命令和材料位置，不等待全员开会才能继续。

使用 AI 开发或制作材料时，先读 docs/AI使用记录规范.md，维护 ai_usage/D/usage.json 和 ai_usage/D/prompts/ 中的实际提示词。每段会话更新原记录，换模型或新会话另建条目；只填可核实的模型、参数、请求数、token 和费用，未知用 null，聊天轮次另记，不能将订阅使用记为 0 元。交接前核对账本，至少有一条真实记录。
