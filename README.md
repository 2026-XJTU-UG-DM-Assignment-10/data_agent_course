# 数据处理智能体课程项目

四人协作、两周展示版。目标是完成固定 Adult 表格数据的质量检测、模型制定清洗计划、工具执行、分类和结果展示。

当前仓库提供公共接口、联调小样本、分工文档与项目结构。数据准备、清洗业务、真实模型调用、分类和页面由四位成员按分工实现，当前没有可运行的完整应用。

## 从哪里开始

1. 阅读[项目任务书](docs/数据处理智能体_AI开发任务书.md)。
2. 全员使用同一版[公共接口说明](docs/公共接口说明.md)和 `src/schema.py`、`src/contracts.py`。
3. 查看[四人分工与协作](docs/四人分工与协作.md)，各自把对应成员任务交给自己的 AI。
4. 当前已有公共文件和小样本，不需要再次从交接包复制。

| 成员 | 主要文件 | 独立任务 | 开发分支 |
| --- | --- | --- | --- |
| A：数据与检测 | `scripts/prepare_data.py`、`src/profiler.py` | [成员 A](docs/成员A_AI任务.md) | `member-a-data` |
| B：规范化与清洗 | `src/normalization.py`、`src/cleaner.py` | [成员 B](docs/成员B_AI任务.md) | `member-b-clean` |
| C：智能体与流程 | `src/llm_client.py`、`src/agent.py`、`src/pipeline.py` | [成员 C](docs/成员C_AI任务.md) | `member-c-agent` |
| D：分类与界面 | `src/classifier.py`、`app.py`、`src/cli.py` | [成员 D](docs/成员D_AI任务.md) | `member-d-ui` |

表中业务文件为待实现文件，未用空实现冒充已完成功能。公共文件和依赖由 D 统一维护，C 维护总流程，其他模块按文件归属修复。

## 环境与当前可运行检查

建议 Python 3.10+。依赖版本取自当前开发环境，公共接口已在 Python 3.13.9、Pydantic 2.12.4 下验证；业务流程完成后还需验证完整依赖组合。

在项目根目录的 PowerShell 中执行：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts/check_contracts.py
```

已有满足依赖的环境时，可以直接执行 `python scripts/check_contracts.py`。该命令检查共享类型、计划校验与样本，不调用模型、不下载数据，也不代表端到端验收已通过。

`examples/` 中为明确标记的微型联调样本，不满足课程规模要求。正式数据由 A 的准备脚本生成，详见 [data/README.md](data/README.md)。

模型配置字段见 `.env.example`，默认值为空；实际密钥放入本地环境变量。当前尚未实现 `.env` 文件自动加载。密钥、虚拟环境、生成数据和运行输出均由 `.gitignore` 排除。

## Git 协作

- `main` 保存集成后的共同起点。
- 每位成员切到自己的分支，只主要修改本人负责文件。
- 交付时附运行命令、实际结果、已知问题及新增依赖，记录到 `docs/handoff_X.md`。
- 通过 PR 或交给集成人合并；公共接口变更统一记录到 [interface_changes.md](docs/interface_changes.md)。
- 不要求每天全员联调：第 4 天规则流程、第 6 天真实模型、第 8 天页面集中联调，第 10 天完整排练。接口变更或出现阻塞时及时同步。

本地切换示例：

```powershell
git switch member-a-data
git status
```

本仓库目前仅在本地创建，尚未配置远程地址。后续在所选托管平台创建空仓库，再将真实地址替换到下面变量中：

```powershell
$projectRemoteUrl = '替换为实际仓库地址'
git remote add origin $projectRemoteUrl
git push -u origin main
git push origin member-a-data member-b-clean member-c-agent member-d-ui
```

远程创建和推送后，其他成员才能通过该地址克隆协作。不要直接执行尚未替换的地址示例。

## 资料位置

- [全部协作文档](docs/README.md)
- [公共数据结构](src/schema.py)
- [函数与模型客户端协议](src/contracts.py)
- [小样本说明](examples/README.md)
- [接口检查记录](docs/公共文件检查记录.md)

正式提交需包含报告、源码、原始及处理后数据、PPT、贡献说明和真实运行日志。生成数据和日志虽不进入 Git，最终仍需另行打包提交。
