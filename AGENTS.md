# 项目协作约定

本项目采用低沟通协作协议 2.0，业务契约保持 1.0，优先完成两周课程展示的最低完整流程。当前用户的明确指令优先于下列默认分工。

## 开始工作

- 先读 `docs/START_HERE.md`，再读 `README.md`、`docs/低沟通协作协议.md`、`collaboration/roles.json` 的本人条目、`docs/公共接口说明.md` 与对应的 `docs/成员X_AI任务.md`。
- 读取本人 `handoffs/X.json`、`docs/handoff_X.md` 和 `docs/integration_log.md`，继续实际未完成项；换 AI 不重新开始。
- 普通实现选择自行解决。只有角色不明、真正缺少外部输入、公共契约冲突或预计延期时需要一次具体沟通。
- 公共文件和小样本已存在，不要再次创建嵌套的 `data_agent_course/` 项目。

## 默认文件归属

- A：数据准备、质量检测、数据说明。
- B：`src/normalization.py`、`src/cleaner.py`。
- C：模型客户端、计划生成、`src/pipeline.py`、日志与导出。
- D：分类、页面、CLI、集成检查，以及公共文件和依赖维护。

完整文件归属以 `collaboration/roles.json` 为准。不要覆盖其他成员尚未提交的工作。冻结 `src/schema.py`、`src/contracts.py`，哈希见 `collaboration/contract_hashes.json`；不得修改哈希绕过检查。必要的公共变更交 D 统一记录和发布，不要求无关人员停工审批。

## 实现边界

- 公共类型从 `src.schema` 导入，不在模块内复制定义。
- 检测和清洗共用 B 的格式规范化，页面和 CLI 共用 C 的总流程。
- 元数据 ID 和标签不作为特征；训练和测试来源组不交叉；所有学得参数只来自训练集。
- 规则模式、模拟故障和真实模型运行明确区分，数字只取自实际运行。
- 不添加多智能体、数据库、部署或模型搜索等范围外功能。
- 密钥不提交、不写日志；未知调用成本使用 null。
- 优先使用共享离线样例，不等待上游完整交付。测试替身只能替代缺失的同伴依赖，不能替代本人的核心实现，也不能隐藏已存在依赖的错误。
- `examples/` 中的摘要、指标和模型返回均有非实验标识；禁止作为真实数据或真实调用证据。

## 验证与交付

- 先运行 `python scripts/check_delivery.py --foundation`，它只检查共享基础，不代表业务完成。
- 本人实现 `checks/check_X.py`，支持 `--integration`；真正运行自己的核心代码，输出实际证据。
- 更新本人 `docs/handoff_X.md` 和 `handoffs/X.json`，执行 `python scripts/check_delivery.py --role X --submit`。通过后才提交为待评审，不能在最后检查后再改已测文件。
- D 在 main 异步运行角色复验和 `scripts/check_integration.py --mode rules/llm`，在集成日志中接受或退回；原负责人修复本人模块。
- 自动检查不能代替实际业务评审。真实模型和端到端验收分别保留证据。
- 全体只需开工确认和展示前排练；第 4/6/8 天为 D 执行的技术检查节点，无需全员在线。
- 检查脚本不自动切分支、合并、重置或推送。归属和流程不是额外要求用户审批的规则。
