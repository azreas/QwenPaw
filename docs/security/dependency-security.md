# Dependency Security

## Local scan

```bash
pip install -e ".[security]"
python scripts/security/dependency_audit.py --project-root .
cd console && npm audit --audit-level=high
cd webchat && npm audit --audit-level=high
```

脚本使用 `--local` + `project_root` 让 pip-audit 只审计项目虚拟环境中的依赖，避免全局安装的无关包（如 uv）污染结果。

## Container filesystem scan

```bash
trivy fs --severity HIGH,CRITICAL --ignore-unfixed .
```

## Ignore file

`scripts/security/pip-audit-ignores.toml` 列出暂不处理的漏洞 ID，每行格式：

```toml
# CVE-XXXX-XXXXX  # 理由
```

脚本默认读取此文件，解析每个漏洞 ID 后逐个传给 `pip-audit --ignore-vuln`。CI 和本地扫描行为一致。

**规则：** 只有已评估风险且确认暂无修复路径的漏洞才可添加 ignore 条目。每次 Dependabot / Renovate 批次处理后应重新评估 ignore 列表。

## Triage

- **Critical** -- 立即修复或 pin 到安全版本。
- **High** -- 本周内修复；如需接受风险，记录到 `docs/security/accepted-risks.md`。
- **Medium / Low** -- 跟随 Dependabot / Renovate 批次处理。
