# 公共接口变更记录

## v1.0：初始公共契约

- 当前共享字段、返回对象和函数签名见 `src/schema.py`、`src/contracts.py` 及公共接口说明。
- 仓库初始化未改变交接包 v1.0 的接口。
- 默认由 D 汇总接口变更，受影响成员同步更新，不在个人模块保留不同版本。

## 协作协议 2.0（业务契约仍为 1.0）

- 固定角色清单、冻结契约哈希、独立开发输入及每角色自测入口。
- 增加机器可读交接、可提交脱敏摘要、待评审检查和 D 的异步复验。
- 任何 AI 从 START_HERE 与本人 prompt 开始，必要时生成单文件开工资料。
- 全体交流保留开工确认和展示前排练，技术检查由 D 执行。
- 未修改 `src/schema.py`、`src/contracts.py` 的业务数据结构和函数协议。

后续记录格式：

```text
日期：
提出成员：
旧接口/字段：
新接口/字段：
变更原因：
影响成员与文件：
兼容或迁移方式：
实际验证结果：
发布版本：
```
# 2026-10-30 第二阶段公共工作流修正

业务契约1.0及两个冻结文件、哈希均不变。在隔离检出用真实prepare_data重建后，A门禁返回2，明确拒绝data/manifests/preparation_summary.json（generated_at变化）。该清单已被main跟踪但未列A归属。

只为A补入三个精确路径：split_manifest.csv、injection_manifest.csv、preparation_summary.json。不放开raw目录、任意data路径或其他业务文件。保留清单跟踪及审计。隔离A门禁修复后实际返回0；12项协作控制回归通过，验证B仍不能修改清单，A不能修改任意额外数据文件。证据见evidence/D/manifest_scope_stage2_20261030.json。
