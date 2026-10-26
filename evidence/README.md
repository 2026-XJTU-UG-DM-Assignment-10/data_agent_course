# 可提交的脱敏验证摘要

成员自测把少量、脱敏的验证摘要写入 `evidence/A/` 至 `D/`，随代码一起提交。完整数据、原始提示词/模型返回、截图和运行日志仍位于本地 data/outputs，最终按课程要求另行打包。

当前没有业务验证摘要，仅有目录标记，不代表角色交付已完成。

每个通过的验证范围对应一个摘要 JSON，例如 `evidence/B/fixtures.json`：

```json
{
  "workflow_version": "2.0",
  "contract_version": "1.0",
  "role": "B",
  "scope": "fixtures",
  "status": "passed",
  "checked_at": "实际执行时间的 ISO 字符串",
  "command": "python checks/check_B.py",
  "uses_test_doubles": false,
  "summary": {"此处放实际检查数量或结果": "不能照抄为已验证"},
  "artifacts": ["outputs/member_B/check.json"]
}
```

此处只是字段示例，不能复制成虚构成功。scope 使用 fixtures/formal_data/real_llm/end_to_end；后三种范围必须使用真实输入/模块/调用，uses_test_doubles=false。

交接 JSON 的 verification.evidence 引用对应 `evidence/X/*.json`。摘要记录完整输出的相对路径，但集成人不需要先拿到队友本机的原始输出才能阅读摘要。集成人按准备命令重建正式数据、实际复验，再保留自己的输出。

checked_at 必须为带时区的实际执行时间，可用 `datetime.now(timezone.utc).isoformat()` 生成，不复制示例占位值。

不要写密钥、鉴权头、密码、Cookie、完整提示词或完整模型返回。运行摘要应简短，不能超过 200 KB。`--integration` 自测只把新输出写入 outputs，不修改成员已经提交的摘要。
