# 2026-11-02 公网 HTTPS 课堂演示入口

公网入口已配置并实际验证：**https://111.230.149.166/**。电脑、手机等支持 HTTPS 的浏览器可直接访问，不需要 SSH 隧道或安装项目依赖。访问时浏览器会要求独立的演示账号；账号为 `demo`，随机强口令通过操作者本机受限文件交付，不提交 Git，不使用 Windows Administrator 密码或 DeepSeek key 作为网页口令。

## 实际部署

| 项目 | 当前配置 |
| --- | --- |
| HTTPS 网关 | 官方 Caddy 2.11.7，安装包通过官方 SHA-512 清单校验 |
| 公网监听 | TCP 443；TCP 80 仅作 HTTPS 跳转及证书验证 |
| TLS | Let's Encrypt 公信 IP 证书，实测 TLS 1.3，证书 SAN 含服务器公网 IP |
| 访问控制 | Caddy basic_auth，全站、媒体、上传、健康检查与 WebSocket 均需认证；服务端仅保存 bcrypt 哈希 |
| 后端 | Streamlit 1.51.0，仍仅监听 127.0.0.1:8501；HTTP 请求体上限21MB，Streamlit上传上限20MiB，应用仍限制20MB |
| 网关服务 | CourseAgentGateway，自动启动，NT AUTHORITY\LocalService，配置失败恢复重启 |
| 应用服务 | CourseAgentApp，官方 WinSW 2.12.0 的 .NET Framework 包，自动启动，NT AUTHORITY\NetworkService |
| 模型配置 | DeepSeek 官方接口、deepseek-flash；key用Windows DPAPI LocalMachine加密，文件ACL仅SYSTEM/Administrators与应用服务账号可读；运行时解密到进程环境 |

Caddy/Streamlit后台服务由Windows服务管理器运行。已实际重启两项服务，并在关闭本机SSH终端和18501隧道后直接从公网复验成功，网页不再依赖这台演示电脑或Codex保持在线。已设置开机自动启动，未实际重启整台服务器；该项与已完成的服务重启测试分别记录。

证书采用支持IP地址的shortlived配置，由Caddy自动维护续期。首张证书有效期为2026-11-02 08:55:48 UTC至2026-11-09 00:55:47 UTC；已验证缓存证书在服务重启后可用，没有等待完整续期周期。实现依据：[Let's Encrypt IP证书说明](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability)、[Caddy ACME profile](https://caddyserver.com/docs/caddyfile/directives/tls)、[Caddy basic_auth](https://caddyserver.com/docs/caddyfile/directives/basic_auth)、[Windows服务](https://caddyserver.com/docs/running)。

此前server_reproduction_20261102.md中“仅通过SSH/配置只在进程内/未配置自启动”描述属于前阶段。以本次部署状态为准；前阶段的运行、指标及证据原样保留。

## 实际验证范围

从本机直接访问公网IP，严格验证证书，未跳过TLS校验或安装自签根证书。14项公网检查全部通过：HTTP 308跳转、匿名访问首页/健康/WSS/媒体及上传被401拒绝、错误口令被拒绝、正确凭据首页与健康检查200、健康正文ok、证书IP SAN匹配、认证WSS握手及streamlit子协议成功。检查脚本仅在本机受限文件读取演示凭据，不在结果中保存凭据。

另从真实网页DOM取得当前混淆矩阵媒体路径，使用公网HTTPS和正确凭据取得PNG，22,438字节，SHA-256 `3e550daa927ac4aa1e467333f96f25261758116d15cca317fda6b6163192634d`，与该次服务器输出逐字节一致。匿名媒体访问被拒绝。

浏览器通过保留的本机隧道操作新后台服务，选择llm并实际点击一次“开始处理”，不是历史回放。运行ID `20261102T100936Z-a2090032`，处理成功，7140→6998训练/3000测试，median/most_frequent，Accuracy 0.8523333333333334、Macro-F1 0.7872823665725043，矩阵[[2108,182],[261,449]]。这次同时验证NetworkService账号能读取正式数据、解密模型配置、调用真实模型、写C账本/业务提示词及导出结果。

该次生产流程新增1次DeepSeek成功请求，输入1262、输出1365 token，无重试，费用未知；C自动记录并原样带回，旧记录保持。项目真实模型调用累计6次，输入5928、输出5652 token。公网连通/认证/WSS检查不算模型请求。本轮聊天不写入开发prompt文档，业务请求仍按项目要求记录。

公网验证覆盖HTTP/HTTPS、认证、WSS及实际PNG；交互式真实处理在同一后台服务的回环网页完成，没有冒充已用手机或教室网络实测。教室电脑仍需在课前实际登录一次；当前未完成课堂网络、手机实机和整机重启测试。

## 使用与维护

课堂打开公网HTTPS链接，在浏览器登录框输入demo及私下交付的口令。默认演示数据和rules可直接使用；现场演示真实模型时选择llm，再点击“开始处理”，会产生新业务请求。网络故障时明确使用已成功历史回放，保留原始run_id与模式标识。

服务器目录：`C:\course_repro_20261102\public_gateway`，配置`Caddyfile`，后台启动`start_app.ps1`，服务日志分别在`gateway_logs`与`app_logs`。模型加密文件独立于源码目录，不通过网关作为静态文件提供。管理员PowerShell维护：

```powershell
Get-Service CourseAgentApp,CourseAgentGateway
Restart-Service CourseAgentApp
Restart-Service CourseAgentGateway
```

Windows镜像原有MpsSvc处于Stopped/Disabled状态，本次没有关闭或启用该全局服务。首次添加Windows防火墙规则因原有服务未运行而失败，保留原状态后继续配置；没有声称已添加成功。云防火墙由操作者此前临时放行全部TCP。建议在腾讯云控制台将80/443保留公网访问，22/3389和8888面板限制管理来源或移除不需要的公网入口；本次没有代替用户修改控制台规则。不能关闭80/443而同时期待公网站点/证书自动验证正常。

回退时仅停止本项目两项服务；不会停止宝塔、其他成员代码或其他网站。旧的SSH访问方式仍可由操作者需要时重新建立，18501隧道已在本轮验证结束前主动关闭。

## 证据与交付

小结`evidence/D/public_gateway_20261102.json`，截图`docs/report_assets/public_gateway_20261102/`。原始包`outputs/public_gateway_20261102/public_gateway_evidence_20261102.zip`包含26项服务快照/启动脚本/新真实运行/C业务记录，逐项SHA-256与解压校验通过；包SHA-256 `cc955bbc211371b1ac2794b9d76492158b5495dcaeaf5e49d65e6afc3f060c3f`。模型加密文件、网页登录口令/哈希配置和证书私钥均未打包。公网、媒体及包校验在同目录的public_check.json、public_media_check.json、package_check.json。

部署中首次网页登录哈希与原口令的独立比对未过，改用独立bcrypt生成并确认Caddy适配结果保持一致后通过正反认证测试；不将早先失败当作成功。业务源码与冻结契约未改，正式PDF/PPT保持原实验版本。排练、录屏及其他未完成课程事项仍分别待办。
