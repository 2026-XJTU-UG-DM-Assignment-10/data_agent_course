# 数据处理智能体课程项目

四人协作、两周展示版。目标是完成固定 Adult 表格数据的质量检测、模型制定清洗计划、工具执行、分类和结果展示。

四个成员的初版已在 main 合并，2026-10-30 完成真实 Adult 规则模式联调，2026-11-02 完成 DeepSeek 真实模型完整验收。训练记录 7,140 → 7,000，测试 3,000；两种模式本次均为 Accuracy 85.23%、Macro-F1 0.7888，实际模型选择同样的 median/Unknown 策略。模型验证、初次验收误报修复和逐次调用证据见[真实模型补验](docs/report_llm_validation_20261102.md)；早前规则联调见[集成记录](docs/integration_20261030.md)。密钥未持久化，新终端仍需本地加载。

2026-11-02异机复现已通过：D在独立Windows Server 2022/Python 3.12.10环境完成依赖安装、正式数据重建、rules/真实LLM集成、网页回放及三份下载哈希检查。验证提交d5d5787；服务器LLM本次选median/most_frequent，训练6,998行，Accuracy85.23%、Macro-F1 0.787282，与上段本机旧运行分别保留。环境、命令、run_id及证据见[服务器复现记录](docs/server_reproduction_20261102.md)。

课堂公网入口已配置：[HTTPS演示网页](https://111.230.149.166/)，需要独立演示账号，口令私下交付。网关/应用已作为自动服务运行，关闭SSH后公网14项检查及媒体下载仍通过；服务重启后真实网页LLM运行20261102T100936Z-a2090032成功，新增1次请求。部署、配置保护、验证范围与维护见[公网入口说明](docs/public_gateway_20261102.md)，本轮不再依赖SSH隧道。

## 从哪里开始

2026-11-02新增：训练分布摘要驱动的策略解释（偏度/四分位数/IQR/缺失率）、14列质量图与实际填补值、历史成功运行回放，以及同结构CSV上传/预检。使用方式、支持范围和实测证据见[功能补全说明](docs/report_adaptive_features_20261102.md)。

1. 从[统一入口](docs/START_HERE.md)开始。协作协议为 2.0，业务契约仍为 1.0。
2. 成员分别把 [A](prompts/A.md)、[B](prompts/B.md)、[C](prompts/C.md)、[D](prompts/D.md) 的开工指令交给自己的 AI；任何模型均需按文件读取规则，不依赖聊天记忆。
3. 遵守[低沟通协作协议](docs/低沟通协作协议.md)、`collaboration/roles.json` 及[公共接口说明](docs/公共接口说明.md)。
4. 查看本人 `handoffs/X.json` 和 `docs/handoff_X.md`，根据[角色任务](docs/README.md)继续开发。
5. 课程功能边界与正式交付物见[项目任务书](docs/数据处理智能体_AI开发任务书.md)。公共文件和样例已准备，不重新创建项目。
6. 按 [AI 使用记录规范](docs/AI使用记录规范.md)维护本人的 `ai_usage/X/usage.json` 和脱敏提示词。开发辅助与项目运行、可核实支出与估算分开；未知参数、请求数和成本如实保留。

| 成员 | 主要文件 | 独立任务 | 开发分支 |
| --- | --- | --- | --- |
| A：数据与检测 | `scripts/prepare_data.py`、`src/profiler.py` | [成员 A](docs/成员A_AI任务.md) | `member-a-data` |
| B：规范化与清洗 | `src/normalization.py`、`src/cleaner.py` | [成员 B](docs/成员B_AI任务.md) | `member-b-clean` |
| C：智能体与流程 | `src/llm_client.py`、`src/agent.py`、`src/pipeline.py` | [成员 C](docs/成员C_AI任务.md) | `member-c-agent` |
| D：分类与界面 | `src/classifier.py`、`app.py`、`src/cli.py` | [成员 D](docs/成员D_AI任务.md) | `member-d-ui` |

表中业务模块已合并；后续仍按成员文件归属维护，公共契约保持 1.0。

## 环境与当前可运行检查

完整依赖要求 Python 3.11+（固定的 NumPy 2.3.5 要求至少 3.11）。本次集成使用 Windows / Python 3.13.9，规则流程、真实模块自测及 Streamlit AppTest 已验证。

在项目根目录的 PowerShell 中执行：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts/check_contracts.py
.venv\Scripts\python.exe scripts/check_delivery.py --foundation
```

已有满足依赖的环境时，可以直接执行 `python scripts/check_contracts.py`。该命令检查共享类型、计划校验与样本，不调用模型、不下载数据，也不代表端到端验收已通过。

`examples/` 包含脏/已规范化/干净小样本，以及模拟摘要、指标、运行结果和模型返回，便于独立开发。它们均非正式实验，见 [fixtures_manifest.json](examples/fixtures_manifest.json)。正式数据由 A 的准备脚本生成，详见 [data/README.md](data/README.md)。

成员实现业务和自测后，用 `python scripts/check_delivery.py --role B --submit`（B 替换为本人角色）生成待评审交付。角色代码尚未实现时返回 not_ready/退出码 2 是预期结果。D 的最终检查入口为 `python scripts/check_integration.py --mode rules` 和 `--mode llm`。

### 准备正式数据并运行

在项目根目录执行；虚拟环境初始化及依赖安装见上面的命令：

```powershell
.venv\Scripts\python.exe scripts/prepare_data.py --seed 42 --sample-size 10000
.venv\Scripts\python.exe -m src.cli --mode rules
.venv\Scripts\python.exe scripts/check_integration.py --mode rules
.venv\Scripts\python.exe -m streamlit run app.py
```

页面默认使用正式训练/测试路径；“查看合成页面示例”仍是单独标记的展示样例。只有点击“开始处理”才创建新运行，重绘和切换模式不会自动请求模型。

真实模型需先设置 `LLM_API_URL`、`LLM_API_KEY`、`LLM_MODEL` 环境变量，再运行 `python scripts/check_integration.py --mode llm`。缺少配置时返回待验证，不降级为规则成功。密钥只在本地设置，不提交或发到聊天中。

集成检查在 main 运行。正式输出为 `outputs/<run_id>/`（smoke 验证使用 `outputs/smoke_runs/<run_id>/`），包括前后质量报告、计划、审计、处理后 CSV、指标、混淆矩阵、摘要和事件日志。`RunResult.artifacts` 的路径均相对于该次运行目录。


模型配置字段见 `.env.example`，默认值为空；实际密钥放入本地环境变量。当前尚未实现 `.env` 文件自动加载。密钥、虚拟环境、生成数据和运行输出均由 `.gitignore` 排除。

需要交给无法直接读取仓库的聊天模型时，执行 `python scripts/build_ai_briefs.py`，将生成的 `outputs/ai_briefs/member_X_AI_brief.md` 整份上传给对应模型。它是当前开工快照，不是运行完成记录。修改交付工具后，可执行 `python checks/check_workflow.py` 回归验证协作控制逻辑；该检查也不代表业务验收。

## Git 协作

- `main` 保存已集成的四人初版与实际复验证据；规则、真实模型及独立服务器复现已通过，排练/录屏等人工验收仍待补。
- 每位成员切到自己的分支，只主要修改本人负责文件。
- 交付时更新本人 `docs/handoff_X.md` 与 `handoffs/X.json`，运行固定自测及交付检查；声明真实数据、真实模型、完整流程各自的实际验证范围。
- 通过 PR 或交给集成人合并；公共接口变更统一记录到 [interface_changes.md](docs/interface_changes.md)。
- 全体交流只保留开工确认和展示前排练。第 4/6/8 天由 D 异步执行技术检查，问题写入 `docs/integration_log.md` 后退回原负责人；无需四人同时在线。

本地切换示例：

```powershell
git switch member-a-data
git status
```

远程仓库：<https://github.com/2026-XJTU-UG-DM-Assignment-10/data_agent_course>，当前为公开仓库。四个成员初版已合入 main，继续开发前先保存并提交个人工作，再执行 git fetch origin 和 git merge origin/main。

项目归属于组织 [2026-XJTU-UG-DM-Assignment-10](https://github.com/2026-XJTU-UG-DM-Assignment-10)，组织显示名称为 `2026_XJTU_Undergraduate_Data_Mining_Course_Assignment_10`。迁移保留原有 Git 提交历史，具体见[仓库迁移说明](docs/仓库迁移说明.md)。

任何人都可以查看和克隆本仓库。队友加入组织后，仍需获得本仓库的 Write 或更高权限才能直接推送；共同管理组织的成员可由现有 Owner 提升为 Owner。以成员 B 为例，先克隆并切换分支：

```powershell
git clone https://github.com/2026-XJTU-UG-DM-Assignment-10/data_agent_course.git
cd data_agent_course
git switch member-b-clean
```

已克隆旧地址的成员，在自己的项目根目录更新远程地址即可：

```powershell
git remote set-url origin https://github.com/2026-XJTU-UG-DM-Assignment-10/data_agent_course.git
git fetch origin
```

在自己的分支完成一小块工作后，先用 `git status` 确认修改文件属于本次交付，再提交和上传：

```powershell
git status
git add .
git commit -m "feat: implement member B cleaning module"
git push -u origin member-b-clean
```

以上提交示例需要在实际完成修改后使用。其他成员替换为自己的分支名和真实提交说明。上传后由集成人根据分支、交接文件和检查报告异步评审并合并到 `main`，无需额外口头讲解。

收到主分支更新通知时，先保存并提交自己的修改，再在个人分支执行 `git fetch origin` 和 `git merge origin/main`。发生冲突时交给集成人共同处理，不需要每天全员联调。

## 资料位置

- [全部协作文档](docs/README.md)
- [公共数据结构](src/schema.py)
- [函数与模型客户端协议](src/contracts.py)
- [小样本说明](examples/README.md)
- [接口检查记录](docs/公共文件检查记录.md)

正式提交需包含报告、源码、原始及处理后数据、PPT、贡献说明和真实运行日志。生成数据和日志虽不进入 Git，最终仍需另行打包提交。

## 正式交付材料（2026-11-02）

[项目报告](docs/report.pdf)共6页，另有[Markdown源文](docs/report.md)；[可编辑PPT](docs/presentation.pptx)共7页，附讲者备注。[PPT制作与课堂展示指南](docs/presentation_guide.md)说明各页重点、7分钟安排、网页点击步骤、答辩与备用方案；[贡献说明](docs/contributions.md)直接列示各成员完成的工作。

当前材料采用公网服务真实运行20261102T100936Z-a2090032：median/most_frequent，训练6,998/测试3,000，Accuracy85.23%、Macro-F1 0.787282；规则对照20261102T084136Z-d398f7b5，训练7,000/测试3,000、Macro-F1 0.788846。输入预检、训练分布与列级解释、历史复用贯穿项目目标和流程。PDF6页/PPT7页逐页渲染、事实交叉检查、3张原生表格、字体、重导入及2张证据图片字节核对通过。

独立服务器环境安装、正式数据重建、rules/真实LLM集成与页面下载已有实际证据。公网入口https://111.230.149.166/配置独立认证与自动后台服务，关闭SSH后访问通过；演示口令私下保管。课前仍需教室网络/投影、原生PowerPoint打开、计时排练及录屏。当前验收范围见[验收清单](docs/acceptance.md)，旧阶段描述保留为历史。

最终包位于outputs/final_release_20261102/data_agent_course_final_20261102.zip，含报告、PPT与课堂指南、完整源码/Git历史、正式数据及实际运行、异机/公网证据、四人AI记录与清单。实际解压/哈希/同机规则运行结果见同目录package_check.json。旧包保留。

材料构建源为docs/report_build.py与docs/presentation_build.mjs；PPT继续编辑保留的原稿，使用Artifact Tool和字节嵌入图片。构建依赖独立于业务requirements；最终PDF/PPT随包提供。材料环境运行`python docs/report_materials_check.py`核对，再在干净main执行`python docs/report_final_package.py --python <已安装业务依赖的解释器>`打包。PPT重新构建使用新的MATERIALS_BUILD_ID，finalizer不覆盖旧产物。

DeepSeek API使用https://api.deepseek.com与deepseek-flash。服务器模型设置已DPAPI加密并限制ACL；其他机器需安全设置LLM_API_URL、LLM_API_KEY、LLM_MODEL，.env不会自动加载。缺配置不会降级为rules成功。模型业务prompt和6次实际请求正常记入C，本次材料制作没有新增项目模型请求。

## AI 使用记录

每段开发会话由 AI 更新本人账本，成员交接前核对；同一会话不重复登记。各人的目录独立维护，随个人分支合并，正式模块交付检查要求本人至少有一条真实记录。

```powershell
python scripts/summarize_ai_usage.py --role B --check --require-records
python scripts/summarize_ai_usage.py
```

第二条命令由 D 合并后运行，生成 `outputs/ai_usage/summary.md` 和 `summary.json`；开发/项目运行分别汇总，未知值不当成零，实际费用与估算、不同币种分别列示。完整账本、提示词与汇总随课程提交包交付；开发记录不能代替真实智能体运行日志。
