# 生产备份

## 策略查询

```bash
curl http://127.0.0.1:8088/api/backups/production/policy
```

返回当前备份策略配置（定时计划、保留天数、存储后端、完整性算法）。

## 完整性校验

每个导出的备份文件应附带 manifest，包含以下字段：

- `filename` — 备份文件名（纯文件名，不含路径分隔符）
- `size_bytes` — 文件大小
- `sha256` — SHA-256 哈希值
- `created_at` — 创建时间（ISO 8601）

通过 API 校验 manifest 与备份文件是否一致：

```bash
curl -X POST http://127.0.0.1:8088/api/backups/production/manifest/verify \
  -H "Content-Type: application/json" \
  -d '{"filename":"backup.zip","size_bytes":1024,"sha256":"...","created_at":"..."}'
```

篡改文件会导致校验失败。filename 不允许包含路径分隔符、`..` 或绝对路径。

## 远程存储

`FilesystemRemoteStore` 将备份文件复制到指定根目录下的子路径。所有 key 均做路径逃逸检查，防止 `../` 等路径穿越。

## 恢复演练

恢复演练通过 backup_id 定位备份文件，解压到服务端自动生成的 sandbox 目录（`BACKUP_DIR/_restore_drills/<uuid>`），不会覆盖当前工作目录或任何生产数据。

```bash
curl -X POST http://127.0.0.1:8088/api/backups/production/drill \
  -H "Content-Type: application/json" \
  -d '{"backup_id":"qwenpaw-0.1-20260510-abc12345"}'
```

演练会检测 zip slip 攻击（如 `../escape.txt`），发现时立即终止并返回错误。

## 调度配置与保留清理

`BackupScheduler` 提供定时备份配置（cron 表达式 + 保留天数）。`cleanup_expired_backups()` 按保留天数清理过期 `.zip` 备份文件。

实际 APScheduler job 注册和 runtime lifecycle 接入待 P3 补齐。

## 健康检查

`/ready` 端点包含 `backup_dir` 组件，检查备份目录是否可写。不可写时标记为 `DEGRADED`，错误信息不会泄露本地敏感路径。
