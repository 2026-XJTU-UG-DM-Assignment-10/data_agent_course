# 2026-11-02 独立云服务器复现结果

结论：异机运行通过。周锦晨（D）完成首次远程登录与 SSH/云防火墙接入，AI 通过 SSH 在独立腾讯云 Windows 服务器执行安装、正式数据重建、rules/真实 DeepSeek 集成及浏览器检查。没有其他成员参与此次操作；符合 acceptance.md 的“异机运行，操作者不限”口径，不代表已完成小组排练或录屏。

## 环境与取得方式

| 项目 | 实际结果 |
| --- | --- |
| 系统 | Windows Server 2022 Datacenter，build 20348，x64 |
| 资源 | 2 个逻辑 CPU，2,146,938,880 字节内存 |
| Python | 独立安装 3.12.10 x64，独立 `.venv`；保留服务器原有 3.8.6 |
| Git | 官方 MinGit 2.56.0.4 x64，发布包 SHA-256 校验通过 |
| 验证提交 | `d5d5787cfb5d641e2eb70fdedbe5950501272163`，main |
| 服务器项目 | `C:\course_repro_20261102\data_agent_course` |
| 实际执行时间 | 2026-11-02 16:38–16:42（北京时间，安装/数据/两种集成）；网页与证据核对随后完成 |

通过加密 SCP 传输完整 Git 历史 bundle、Python 官方安装包、MinGit 官方包、51 个 PyPI wheel 和哈希一致的 UCI Adult 原始文件，55 个传输文件哈希全部一致。服务器从 bundle 新建 main 检出并核对指定提交、创建新虚拟环境、实际安装依赖；不是复制本地虚拟环境或成功输出。Python 安装包 Authenticode 签名为有效的 Python Software Foundation 签名。依赖通过 `pip check`，实际版本保存在 `reproduction_logs/pip_freeze.log`。

原始 Adult 文件 SHA-256 为 `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`。服务器使用该官方原始文件重新生成 10,000 条参考样本、7,140 条脏训练和 3,000 条测试；没有声称在服务器重新从 UCI/PyPI 下载缓存文件。训练/测试 CSV、划分与注入清单的哈希均与本机一致；准备摘要的时间元数据是本次新生成值。

## 实际命令与结果

下列 python 均指服务器项目的 `.venv\Scripts\python.exe`。记录的 12 条环境/业务命令退出码均为 0，逐条起止时间、参数及日志位于 `reproduction_logs/commands.jsonl`。

```powershell
python -m pip install --no-index --find-links C:\course_repro_20261102_upload\payload\wheelhouse -r requirements.txt
python -m pip check
python scripts/prepare_data.py --seed 42 --sample-size 10000
python scripts/check_integration.py --mode rules
# 仅向进程加载真实模型配置后执行；密钥不在命令参数中
python scripts/check_integration.py --mode llm
```

| 项目 | rules | 真实 llm |
| --- | --- | --- |
| 整体/四角色复验 | passed / A、B、C、D passed | passed / A、B、C、D passed |
| 退出码 | 0 | 0 |
| run_id | `20261102T084136Z-d398f7b5` | `20261102T084237Z-decc1cbf` |
| 训练行数 | 7,140 → 7,000 | 7,140 → 6,998 |
| 测试行数 | 3,000 | 3,000 |
| 数值/类别策略 | median / constant Unknown | median / most_frequent |
| Accuracy | 0.8523333333333334 | 0.8523333333333334 |
| Macro-F1 | 0.788845681782975 | 0.7872823665725043 |
| 混淆矩阵（行真实、列预测；<=50K、>50K） | [[2101,189],[254,456]] | [[2108,182],[261,449]] |

服务器规则结果与本机一致。真实模型本次选了不同的合法类别策略，并在理由中引用训练缺失率与偏度/四分位数。类别改用众数后，填补前去重 140 行、填补后又去重 2 行，因此训练剩 6,998 行；不能把旧运行的 7,000 行或 Macro-F1 抄成本次结果。两种模式处理后四类质量问题均为 0，测试保留全部 3,000 行，输入未被流程改写、来源组隔离和 train-only 拟合边界通过实际 smoke 检查。此次 LLM 没有带来分类指标提升。

DeepSeek 官方接口、模型 `deepseek-flash`，temperature=0，超时 90 秒、调用预算 2。实际发出 1 次请求并成功，无重试/纠错；输入 1,262、输出 1,418 token，费用未知。C 的生产 pipeline 自动生成该次业务请求账本与业务提示词；原有 4 条调用记录保留，新增记录逐字段复制且无重复。全项目当前共 5 次实际请求，输入 4,666 / 输出 4,287 token；开发会话另计。本轮聊天输入不写入开发 prompt 文档。

## 网页与下载

Streamlit 实际运行在服务器 `127.0.0.1:8501`，通过本机回环 SSH 隧道 `127.0.0.1:18501` 检查，网页未绑定公网地址。浏览器成功加载服务器新 LLM 运行的历史结果，明确显示原始 run_id、历史回放提示、6,998 行、四类问题归零、median/most_frequent 理由、14 列质量图/分布、实际训练填补值及上述分类矩阵。

13 个运行文件下载入口可见；实际下载 `train_processed.csv`、`events.jsonl`、`summary.md`，与服务器对应文件逐字节一致。其他 10 个文件由完整 smoke 检查其存在性、schema/内容与路径边界，本次没有逐个通过浏览器下载，不扩大浏览器验证结论。回放/展开图表/下载未新增模型请求。

| 实际浏览器下载 | 字节 | SHA-256 |
| --- | --- | --- |
| train_processed.csv | 1,037,803 | `65ab63c9c5878d21b66b4d9be5f326d43d3219b33f03ccfd6be1e32e3dc85cb0` |
| events.jsonl | 22,119 | `7e443d3c2907871c2f1176181e5ece16cc2376409695b272c9a1b09198324691` |
| summary.md | 180 | `21b572020cc071d36d5e2ba0b69f24b7d01201d1e8f0bd4cc8ed007a1dc1b5fb` |

网页进程随后加载相同 DeepSeek 配置，密钥仅保留在运行进程内存；未持久化到文件/用户环境/系统环境。后续点击“开始处理”才会产生新请求。当前 SSH 网页连接关闭或服务器重启后，需重新启动网页并加载配置；不能将当前运行描述为已配置自启动服务。

服务器浏览器可直接打开 `http://127.0.0.1:8501`。演示电脑建立隧道后打开 `http://127.0.0.1:18501`：

```powershell
ssh -N -L 127.0.0.1:18501:127.0.0.1:8501 Administrator@服务器公网IP
```

服务器内重新启动网页（先在该进程安全加载 API 配置；不把密钥放入启动参数）：

```powershell
cd C:\course_repro_20261102\data_agent_course
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

云防火墙由操作者临时放行全部 TCP 后接通；复现和 SSH 隧道只需 TCP 22，远程桌面另需 3389，可由操作者将临时规则收紧到所需端口及来源 IP。没有自动关闭防火墙或降低认证要求。

## 证据、问题与未验证项

公开小结为 `evidence/D/server_reproduction_20261102.json`，页面截图在 `docs/report_assets/server_20261102/`。原始证据包位于本机 `outputs/server_reproduction_20261102/server_evidence_verified_20261102.zip`，服务器也保留同名文件。包含正式数据、两次实际成功目录、集成报告、C 业务调用记录及命令/环境日志；61 个文件逐一校验后解压通过，包 SHA-256 为 `3d5d13490940aa7be45afd29a0a6227bfe74c1966b9f81d8b36385a6b90233df`。校验及浏览器下载对比为同目录 `package_check.json`。

实际接入曾受云防火墙拦截；初次辅助启动脚本在 Windows PowerShell 的默认路径参数绑定失败，显式传入 payload 路径后完成安装。打包时活动网页日志被锁，改为排除两份活动日志、保留已完成命令日志后成功打包。Windows PowerShell 读取中文 JSON 需显式 UTF-8；这些操作问题没有冒充业务检查失败或隐去重试。最终业务两种模式的命令均一次退出 0。

本轮没有改业务模块、冻结契约或覆盖其他成员工作。正式 PDF/PPT 保留前阶段实验快照，本补充记录单独列明服务器新实测；没有重写旧实验数字。原生 PowerPoint 打开、小组排练/录屏、课堂网络及 B 案例文字确认仍待实际完成；服务器复现不替代这些事项。
