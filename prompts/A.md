# 发给成员 A 所用 AI 的开工指令

我是成员 A，请在现有项目根目录按协作协议 2.0 开发数据与检测，不重建项目。

先读取 AGENTS.md、README.md、docs/START_HERE.md、docs/低沟通协作协议.md、collaboration/roles.json 的 A 条目、docs/公共接口说明.md、src/schema.py、src/contracts.py、docs/成员A_AI任务.md，以及本人的交接和集成退回记录。

使用 member-a-data 分支，只主要修改 A 归属的文件。先用共享样例独立开发，B 的依赖尚未提供时可以在自测中使用明确标记的替身，生产代码不得藏替身。不等待全员在线，不私改冻结契约。

实现并实际运行 checks/check_A.py（需支持 --integration），填写 docs/handoff_A.md、handoffs/A.json，再执行 python scripts/check_delivery.py --role A --submit。检查通过后按仓库协作规则提交个人分支。最终给出变更、命令、实际结果、未验证项及下一步。

若你不能读取工作区，请先列出缺少的上述文件；若不能执行代码，输出文件内容和待执行命令，并把运行结果保留 not_run，不能声称已通过。角色和文件已明确时，不重复追问普通实现选择。
