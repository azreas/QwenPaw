# Kubernetes / Helm 部署

## 前提

- Kubernetes 集群已就绪
- Helm v3 已安装
- 外部 Postgres 和 Redis 已部署

## Secret

生产环境必须预先创建 Secret：

```bash
kubectl create namespace qwenpaw
kubectl -n qwenpaw create secret generic qwenpaw-prod-secret \
  --from-literal=QWENPAW_DATABASE_URL='postgresql+asyncpg://qwenpaw:change-me@postgres:5432/qwenpaw' \
  --from-literal=QWENPAW_REDIS_URL='redis://redis:6379/0' \
  --from-literal=QWENPAW_WEBCHAT_SESSION_SECRET='replace-with-32-byte-secret' \
  --from-literal=QWENPAW_CORS_ORIGINS='https://qwenpaw.example.com'
```

## Install

```bash
helm upgrade --install qwenpaw deploy/helm/qwenpaw \
  --namespace qwenpaw \
  --values deploy/helm/qwenpaw/values-prod.yaml
```

开发环境：

```bash
helm upgrade --install qwenpaw deploy/helm/qwenpaw \
  --namespace qwenpaw \
  --values deploy/helm/qwenpaw/values-dev.yaml
```

## Verify

```bash
kubectl -n qwenpaw rollout status deploy/qwenpaw-qwenpaw
kubectl -n qwenpaw port-forward svc/qwenpaw-qwenpaw 8088:8088
curl http://127.0.0.1:8088/health
curl http://127.0.0.1:8088/ready
```

## Upgrade

```bash
helm diff upgrade qwenpaw deploy/helm/qwenpaw \
  --namespace qwenpaw \
  --values deploy/helm/qwenpaw/values-prod.yaml
helm upgrade qwenpaw deploy/helm/qwenpaw \
  --namespace qwenpaw \
  --values deploy/helm/qwenpaw/values-prod.yaml
```

## Rollback

```bash
helm -n qwenpaw history qwenpaw
helm -n qwenpaw rollback qwenpaw 1
```

## Values Overlay

| 文件 | 用途 |
| --- | --- |
| `values-dev.yaml` | 本地开发，SQLite，低资源 |
| `values-staging.yaml` | 预发布，Postgres，Ingress 开启，existingSecret |
| `values-prod.yaml` | 生产，Postgres，Ingress 开启，existingSecret，高资源 |

## 探针

| 探针 | 路径 | 说明 |
| --- | --- | --- |
| liveness | `/health` | 进程存活检测 |
| readiness | `/ready` | 依赖就绪检测（DB、Redis 等） |
| startup | `/health` | 启动慢启动保护 |

## 持久化

| PVC | 挂载路径 | 默认大小 | 用途 |
| --- | --- | --- | --- |
| working | `/app/working` | 20Gi | 工作目录 |
| secrets | `/app/working.secret` | 2Gi | 密钥目录 |
| backups | `/app/working.backups` | 50Gi | 备份目录 |

---

## 企业化测试环境

本章节用于企业化测试部署，目标是提供三线联调可复用的基准环境。

### 环境说明

| 环境 | values overlay | Secret |
| --- | --- | --- |
| staging | `values-staging.yaml` | `qwenpaw-staging-secret` |
| pilot | `values-prod.yaml` | `qwenpaw-prod-secret` |

### Secret 注入

使用 `existingSecret` 模式注入敏感配置，避免明文写入 values：

```bash
# 创建 staging 环境 Secret
kubectl create namespace qwenpaw-staging
kubectl -n qwenpaw-staging create secret generic qwenpaw-staging-secret \
  --from-literal=QWENPAW_DATABASE_URL='postgresql+asyncpg://qwenpaw:change-me@postgres:5432/qwenpaw' \
  --from-literal=QWENPAW_REDIS_URL='redis://redis:6379/0' \
  --from-literal=QWENPAW_WEBCHAT_SESSION_SECRET='replace-with-32-byte-secret' \
  --from-literal=QWENPAW_CORS_ORIGINS='https://staging-ai.example.com' \
  --from-literal=QWENPAW_WEBCHAT_SSO_LOGIN_URL='https://sso.example.com/login' \
  --from-literal=QWENPAW_WEBCHAT_QRCODE_LOGIN_URL='https://qyapi.example.com/login'
```

完整环境变量样例见 `deploy/env/enterprise-test.env.example`。

### 部署后验证

部署后必须依次访问：

```bash
# 进程存活
curl http://<staging-host>/health

# 依赖就绪
curl http://<staging-host>/ready

# 企业化 readiness 诊断
curl http://<staging-host>/api/enterprise/readiness
```

`/api/enterprise/readiness` 返回值：
- `ready`: 所有必填项通过，可进入联调
- `degraded`: 部分可选项缺失，核心功能可用
- `blocked`: 有必填项缺失，无法进入联调

### 回滚

```bash
helm -n qwenpaw-staging history qwenpaw-staging
helm -n qwenpaw-staging rollback qwenpaw-staging <revision>
```
