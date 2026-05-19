# 企业级扩展说明

本文说明 QwenPaw 当前企业化分支的多租户平台能力。内容面向公开仓库阅读，聚焦项目定位、能力概览、使用入口、运行配置和使用边界。

## 项目定位

QwenPaw 当前企业化分支定位为企业级多租户 AI 平台，围绕 `wx_*` 动态租户工作区、Enterprise Admin 管理后台、WebChat 员工入口、企微 Bot、租户级能力配置、RBAC、审计追踪和运行保障组织产品能力。

上游个人助手和旧 Console 经验仅作为迁移参考；企业部署的长期管理入口是 Enterprise Admin，员工侧入口由 WebChat 和企业微信 Bot 承载。

## 能力概览

| 能力域 | 当前扩展 |
| --- | --- |
| 企业入口 | 支持 WebChat 和企业微信 Bot 作为员工入口。 |
| 多租户工作区 | 支持按企业身份映射到 `wx_*` 动态租户工作区，隔离会话、文件、配置和能力。 |
| 租户级配置 | 支持租户级模型、Tools、Skills、MCP、安全规则、系统提示词和定时任务配置。 |
| 企业权限 | 支持企业工作台登录、多用户、角色和租户绑定，并通过 RBAC 做管理权限控制；Console 仅保留迁移期参考入口。 |
| 业务能力承载 | 支持将业务 Skills 和 MCP 服务接入租户工作区，并在 WebChat、企业微信和后台中复用。 |
| 审计追踪 | 支持登录、权限拒绝、配置变更、Skills/MCP 调用、Bad Case 等事件记录。 |
| 运营管理 | 企业工作台承载租户管理、运营摘要、业务调用追踪、Bad Case 和测评能力；Console 保留为迁移期参考。 |
| 生产保障 | 支持健康检查、readiness 诊断、结构化日志、配额、备份恢复、Docker 和 Kubernetes 部署配置。 |

## 使用入口

### 员工侧

- **WebChat：** 企业内部聊天入口，适合完整会话、历史记录、文件上传和个人工作台体验。
- **企业微信 Bot：** 高频轻量入口，适合在企业微信中直接发起问答和任务。

两个入口都应使用同一套企业身份字段，进入同一个 `wx_*` 租户工作区，避免会话、文件和能力配置分叉。

### 管理侧

- **平台用户管理：** 管理企业工作台后台用户、角色和租户绑定。
- **企业微信租户管理：** 管理租户启停、入口配置、模型路由、Skills、MCP、Tools、安全规则、系统提示词、文件、Cron 和运行资源。
- **运营与追踪：** 查看租户状态、调用趋势、失败记录、业务调用追踪、Bad Case、验收测评、配额和指标摘要。
- **平台诊断：** 查看 readiness、企业运行时状态、租户 health、入口配置诊断、备份策略和恢复演练结果。

策略中心和系统设置目前保留为阶段化开放入口，不应被对外描述为完整可用能力。

## 核心链路

```text
WebChat / 企业微信 Bot
  -> 企业身份解析
  -> wx_* 动态租户工作区
  -> AgentRunner / QwenPawAgent
  -> Tools / Skills / MCP / Memory
  -> 审计追踪 / 配额 / 运营后台
```

管理后台与员工入口共享同一套租户、权限和审计上下文：

```text
企业工作台（Enterprise Admin）管理后台
  -> 用户、角色、租户绑定
  -> 租户级能力配置
  -> 运营总览、调用追踪、Bad Case
  -> Enterprise Runtime / RBAC / Audit / Storage
```

## 关键目录

| 目录或文件 | 说明 |
| --- | --- |
| `src/qwenpaw/enterprise/` | 企业运行时、权限、策略、配额、审计、可观测性、可靠性和合规能力。 |
| `src/qwenpaw/tenancy/` | 动态租户、租户路径和工作区配置。 |
| `src/qwenpaw/app/routers/webchat.py` | WebChat API 入口。 |
| `src/qwenpaw/app/routers/wecom_tenant_config/` | 企业微信租户配置、运营和 Bad Case API。 |
| `src/qwenpaw/app/channels/` | IM 渠道接入，包括企业微信租户通道。 |
| `console/src/pages/Control/WecomTenants/` | 迁移期参考的 Console 企业微信租户管理页面。 |
| `console/src/pages/Platform/Users/` | 迁移期参考的 Console 用户、角色和租户绑定页面。 |
| `webchat/` | 企业内部 WebChat 前端。 |
| `deploy/` | Docker、Helm 和部署配置。 |
| `docs/deploy/` | 部署说明。 |
| `docs/backup/` | 备份恢复说明。 |
| `docs/compliance/` | 审计导出和合规说明。 |

## 使用模式和鉴权

### 本地试用模式

默认不设置 `QWENPAW_AUTH_ENABLED=true` 时，后台认证处于关闭状态，适合本地试用、单人调试和公开仓库快速体验。此时 `/api/models`、`/api/plan/config` 等管理 API 不需要 Bearer Token。

如果已经开启过认证，又想回到本地试用模式，请确认：

- 没有设置 `QWENPAW_AUTH_ENABLED=true`。
- 启动进程使用的是当前仓库代码和当前 Python 环境。
- 浏览器里旧的登录态不会影响接口判断，必要时清理本地存储后刷新页面。

### 企业受保护模式

企业内部使用建议显式开启企业管理认证，并设置初始管理员：

```bash
export QWENPAW_AUTH_ENABLED=true
export QWENPAW_AUTH_USERNAME=admin
export QWENPAW_AUTH_PASSWORD=change-me
qwenpaw app
```

Windows PowerShell 示例：

```powershell
$env:QWENPAW_AUTH_ENABLED = "true"
$env:QWENPAW_AUTH_USERNAME = "admin"
$env:QWENPAW_AUTH_PASSWORD = "change-me"
qwenpaw app
```

首次启动时，如果密钥目录中还没有用户，系统会自动创建初始管理员。之后可以通过企业工作台登录，也可以调用 `POST /api/auth/login` 获取 Token。受保护的管理 API 需要携带：

```http
Authorization: Bearer <token>
```

`platform_admin` 具备平台管理权限；租户管理员和租户成员需要绑定 `tenant_id`，否则只能访问其角色允许的资源。

### WebChat 员工入口

WebChat 不复用后台管理员 Token。员工侧入口使用 WebChat Session Token、企业 SSO 或企业微信扫码配置来识别用户，再映射到对应的 `wx_*` 租户工作区。

生产环境至少应显式设置：

- `QWENPAW_WEBCHAT_SESSION_SECRET`
- `QWENPAW_WEBCHAT_SSO_LOGIN_URL` 或 `QWENPAW_WEBCHAT_QRCODE_*`

### 403 排查

| 现象 | 常见原因 | 处理方式 |
| --- | --- | --- |
| 本地访问 `/api/models`、`/api/plan/config` 返回 403 | 启用了后台认证，但请求没有携带 Token，或启动的不是当前仓库代码 | 检查 `QWENPAW_AUTH_ENABLED`，重新启动服务；开启认证时先登录企业工作台或携带 Bearer Token。 |
| 登录后仍然返回 403 | 用户角色不包含目标资源权限，或租户用户没有绑定对应 `tenant_id` | 使用平台管理员检查用户角色和租户绑定。 |
| WebChat API 返回 403 | WebChat Session Token 缺失、过期或签名密钥不一致 | 重新登录 WebChat，确认 `QWENPAW_WEBCHAT_SESSION_SECRET` 与当前服务一致。 |
| 企业微信或 WebChat 进入了不同工作区 | 企业身份字段不稳定，或入口没有映射到同一个 `wx_*` 租户 | 检查企业身份映射和租户工作区配置。 |

## 运行方式

### 本地开发

```bash
# 后端
pip install -e ".[dev,full]"
qwenpaw init --defaults
qwenpaw app

# Enterprise Admin
cd enterprise-admin
npm install
npm run dev

# WebChat
cd webchat
npm install
npm run dev
```

在源码仓库内调试后端时，也可以使用仓库脚本启动当前 checkout 的企业化扩展版本：

```powershell
.venv\Scripts\python.exe scripts\start_backend_debug.py --port 8088 --log-level debug
```

该脚本会把当前仓库的 `src/` 加入 Python 导入路径，并准备工作目录、密钥目录、临时目录以及 Enterprise Admin 静态资源路径。缺少企业工作台构建产物时，可以先执行 Enterprise Admin 构建；Console 仅作为迁移期参考入口，需显式设置 `QWENPAW_CONSOLE_ENABLED=true` 并准备对应静态资源。只调后端 API 时，可临时加 `--allow-missing-console`。

### 生产构建

```bash
npm --prefix enterprise-admin run build
npm --prefix webchat run build
qwenpaw app
```

生产环境建议至少显式配置：

| 环境变量 | 用途 |
| --- | --- |
| `QWENPAW_WORKING_DIR` | 工作目录。 |
| `QWENPAW_SECRET_DIR` | 密钥目录。 |
| `QWENPAW_AUTH_ENABLED` | 启用企业管理认证 / 后台登录认证。 |
| `QWENPAW_AUTH_USERNAME` / `QWENPAW_AUTH_PASSWORD` | 初始管理员账号和密码。 |
| `QWENPAW_ENTERPRISE_ADMIN_STATIC_DIR` | 企业工作台静态资源路径。 |
| `QWENPAW_CONSOLE_ENABLED` | 迁移期是否显式开启旧 Console 入口。 |
| `QWENPAW_CONSOLE_STATIC_DIR` | 迁移期旧 Console 构建产物目录。 |
| `QWENPAW_WEBCHAT_SESSION_SECRET` | WebChat Session 签名密钥。 |
| `QWENPAW_WEBCHAT_SSO_LOGIN_URL` | 企业 SSO 登录地址。 |
| `QWENPAW_WEBCHAT_QRCODE_*` | 企业微信扫码登录配置。 |
| `QWENPAW_STORAGE_BACKEND` | 企业存储后端。 |
| `QWENPAW_DATABASE_URL` | 数据库连接串。 |
| `QWENPAW_REDIS_URL` | Redis 地址，用于配额和可靠性能力。 |
| `QWENPAW_LOG_FORMAT` | 设为 `json` 时启用结构化日志。 |

## 验证建议

公开仓库中可以优先执行以下验证：

```bash
# 后端测试
pytest

# Enterprise Admin 构建
cd enterprise-admin
npm run build

# WebChat 构建
cd webchat
npm run build
```

如使用企业化部署配置，可参考：

- [企业化测试部署](../deploy/enterprise-test-deployment.md)
- [Kubernetes 部署](../deploy/kubernetes.md)
- [生产备份恢复](../backup/production.md)
- [审计导出](../compliance/audit-export.md)

## 使用边界

- 当前 fork 的企业级能力是对上游 QwenPaw 的扩展，不代表上游默认发行版具备全部企业后台能力。
- WebChat、企业微信 Bot、SSO、数据库、Redis、MCP 服务和域名证书需要按实际企业环境配置。
- 业务指标口径、业务 SQL、业务知识库和标准问法需要由业务或数据团队提供；平台侧负责接入、授权、运行、追踪和排障。
- 不同员工、租户和工作区应使用稳定的企业身份字段做映射，避免会话和文件空间分叉。
- 高风险工具和外部 MCP 服务应结合 RBAC、ToolGuard、审计和部署环境做额外控制。
