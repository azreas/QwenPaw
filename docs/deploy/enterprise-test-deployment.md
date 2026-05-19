# 企业化测试部署手册

## 1. 部署目标

本手册用于企业化测试环境，不用于直接替代生产变更单。目标是提供一套可重复、可验证、可观测的部署基准，让个人入口、企业后台和数据团队按契约接入。

## 2. 环境矩阵

| 环境 | 用途 | 域名 | 镜像 tag | 存储 | Redis | Postgres | 入口 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dev | 本地和开发自测 | http://127.0.0.1:8088 | local | SQLite | 可选 | 可选 | Console + WebChat |
| staging | 三线联调 | 由运维分配 | qwenpaw-enterprise-test | PVC | 必配 | 必配 | Console + WebChat + 企微 |
| pilot | 试点用户验证 | 由运维分配 | qwenpaw-pilot | PVC | 必配 | 必配 | WebChat + 企微 |

## 3. Secret 清单

| 变量 | 是否必填 | 用途 | 示例 |
| --- | --- | --- | --- |
| QWENPAW_WEBCHAT_SESSION_SECRET | 是 | WebChat token 签名 | replace-with-32-byte-secret |
| QWENPAW_AUTH_ENABLED | 是 | Console 登录保护 | true |
| QWENPAW_DATABASE_URL | staging/pilot 必填 | SQL 存储 | postgresql+asyncpg://user:pass@host:5432/qwenpaw |
| QWENPAW_REDIS_URL | staging/pilot 必填 | 配额和死信队列 | redis://redis:6379/0 |
| QWENPAW_WEBCHAT_SSO_LOGIN_URL | SSO 联调必填 | WebChat SSO 登录 | https://sso.example.com/login |
| QWENPAW_WEBCHAT_QRCODE_LOGIN_URL | 扫码联调必填 | 企微扫码登录 | https://qyapi.example.com/login |
| QWENPAW_CORS_ORIGINS | staging/pilot 必填 | CORS 白名单 | https://ai.example.com |

## 4. Helm 部署

使用 `deploy/helm/qwenpaw/values-staging.yaml` 作为三线联调基础配置：

```bash
# 创建命名空间
kubectl create namespace qwenpaw-staging

# 预先创建 Secret（不要提交到代码仓库）
kubectl -n qwenpaw-staging create secret generic qwenpaw-staging-secret \
  --from-literal=QWENPAW_DATABASE_URL='postgresql+asyncpg://qwenpaw:change-me@postgres:5432/qwenpaw' \
  --from-literal=QWENPAW_REDIS_URL='redis://redis:6379/0' \
  --from-literal=QWENPAW_WEBCHAT_SESSION_SECRET='your-32-byte-secret-here' \
  --from-literal=QWENPAW_CORS_ORIGINS='https://staging-ai.example.com' \
  --from-literal=QWENPAW_WEBCHAT_SSO_LOGIN_URL='https://sso.example.com/login' \
  --from-literal=QWENPAW_WEBCHAT_QRCODE_LOGIN_URL='https://qyapi.example.com/login'

# 部署
helm upgrade --install qwenpaw-staging deploy/helm/qwenpaw \
  --namespace qwenpaw-staging \
  --values deploy/helm/qwenpaw/values-staging.yaml
```

## 5. Docker 部署

本地快速企业化测试验证：

```bash
# 构建镜像
docker build -t qwenpaw-enterprise-test -f deploy/Dockerfile .

# 使用环境变量文件启动
docker run -d \
  --name qwenpaw-enterprise-test \
  -p 8088:8088 \
  -v $(pwd)/working:/app/working \
  -v $(pwd)/working.secret:/app/working.secret \
  -v $(pwd)/working.backups:/app/working.backups \
  -e QWENPAW_WORKING_DIR=/app/working \
  -e QWENPAW_SECRET_DIR=/app/working.secret \
  -e QWENPAW_STORAGE_BACKEND=json \
  -e QWENPAW_AUTH_ENABLED=true \
  -e QWENPAW_WEBCHAT_SESSION_SECRET=your-32-byte-secret-here \
  qwenpaw-enterprise-test
```

## 6. 健康检查

部署后必须依次验证以下健康检查：

| 检查项 | 命令 | 通过标准 |
| --- | --- | --- |
| liveness 探针 | `curl http://<host>/health` | 返回 `{"status":"ok"}` |
| readiness 探针 | `curl http://<host>/ready` | 返回 `{"ready": true, "status": "up", "components": [...]}` |
| 企业化 readiness（公开） | `curl http://<host>/api/enterprise/readiness` | 仅返回 `{"status": "ready" | "degraded" | "blocked"}` |
| 企业化 readiness（管理员） | 使用 Console 管理员 token 调用 | 返回完整 `checks` 和 `blockers` 详情 |

> 安全说明：公开访问 `/api/enterprise/readiness` 只返回粗粒度状态，避免泄露企业依赖配置；详细检查信息需要 `platform_admin` 权限。

## 7. SSO / 企微 / MCP 依赖检查

### SSO 与企微身份契约

| 字段 | 来源 | 平台处理 |
| --- | --- | --- |
| employee_id | SSO | 作为 WebChat 用户身份 |
| wechat_company_id | SSO | 必须与企微 userid 一致 |
| from.userid | 企微回调 | 作为租户主键 |
| agent_id | 平台生成 | `tenant_agent_id(tenant_id)`，格式为 `wx_*` |

### 依赖检查清单

```bash
# 检查 SSO 可达性
curl -I $QWENPAW_WEBCHAT_SSO_LOGIN_URL

# 检查企微扫码登录可达性
curl -I $QWENPAW_WEBCHAT_QRCODE_LOGIN_URL

# 检查 MCP 服务可达性
curl <MCP_SERVICE_URL>/health
```

## 8. 数据团队接入前的 mock 能力

平台底座提供 mock MCP 响应契约，用于验证入口、权限、追踪、失败原因和 Bad Case 分派。数据团队接入真实 MCP 服务时，必须保持以下字段：

| 字段 | 说明 |
| --- | --- |
| status | success / failure / denied |
| ability_type | skill 或 mcp |
| ability_name | 能力名称 |
| answer | 成功结果 |
| error_reason | 失败原因 |
| request_id / trace_id | 平台追踪字段 |

## 9. 备份恢复演练

企业化测试环境必须执行一次备份恢复演练：

```bash
# 1. 创建备份
kubectl -n qwenpaw-staging exec deploy/qwenpaw-staging-qwenpaw -- qwenpaw backup --output /app/working.backups

# 2. 验证备份文件
kubectl -n qwenpaw-staging exec deploy/qwenpaw-staging-qwenpaw -- ls -la /app/working.backups

# 3. 恢复演练（先停止服务，恢复后重启）
kubectl -n qwenpaw-staging scale deploy/qwenpaw-staging-qwenpaw --replicas=0
# 执行恢复操作
kubectl -n qwenpaw-staging scale deploy/qwenpaw-staging-qwenpaw --replicas=1

# 4. 验证恢复后数据
kubectl -n qwenpaw-staging exec deploy/qwenpaw-staging-qwenpaw -- qwenpaw doctor
```

## 10. 回滚

部署失败时的回滚操作：

```bash
# 查看历史版本
helm -n qwenpaw-staging history qwenpaw-staging

# 回滚到上一版本
helm -n qwenpaw-staging rollback qwenpaw-staging

# 验证回滚结果
kubectl -n qwenpaw-staging rollout status deploy/qwenpaw-staging-qwenpaw
curl http://<host>/health
```

## 11. 交付检查表

| 检查项 | 完成状态 | 负责人 | 备注 |
| --- | --- | --- | --- |
| Secret 全部配置 | | 运维 | |
| Postgres 数据库就绪 | | 运维 | |
| Redis 就绪 | | 运维 | |
| SSO 登录可达 | | 运维 | |
| 企微扫码登录可达 | | 运维 | |
| Console 可访问 | | 个人入口 | |
| WebChat 可访问 | | 个人入口 | |
| 备份恢复演练完成 | | 平台底座 | |
| /api/enterprise/readiness 返回 ready | | 平台底座 | |

## 平台底座验证命令

Windows:

```powershell
.\scripts\enterprise_foundation_check.ps1
```

Linux/macOS:

```bash
bash scripts/enterprise_foundation_check.sh
```
