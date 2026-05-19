# QwenPaw 项目定位索引

本文件只记录项目特有信息，用于新需求和代码改动时快速定位。通用协作、验证、安全和 Git 规则遵循用户级 `AGENTS.md`；共享需求契约、项目协作和阶段材料分别参考 `openspec/README.md`、`docs/team-collaboration.md` 和 `docs/superpowers/README.md`。

## 协作入口

- **项目协作手册：** `docs/team-collaboration.md`，说明 OpenSpec、Superpowers、PR / MR 和 AI 协作方式。
- **需求契约：** `openspec/README.md`、`openspec/specs/`。新增功能、共享契约、身份 / 权限 / 会话 / 审计 / 租户边界变更先走 OpenSpec change。
- **执行沉淀：** `docs/superpowers/README.md`。Superpowers 只承接已确认需求的执行计划、验证结果、阶段报告和 closeout。
- **职责边界：** OpenSpec 只管理需求契约和能力变更边界；代码实现、调试、测试、执行计划和阶段落地必须使用 Superpowers 相关技能与 `docs/superpowers/` 流程沉淀，不使用 `openspec apply` 承接实现任务。
- **项目定位：** 本文件继续作为 Agent 和新线程的轻量导航，不复制全局开发规则，也不替代 OpenSpec 的需求契约。

## 项目概览

- **项目名：** QwenPaw，原 CoPaw。
- **定位：** 基于 AgentScope 的企业级多租户 AI 平台。
- **后端：** Python FastAPI + ReAct Agent，源码位于 `src/qwenpaw/`。
- **前端：** 三个 Vite + React 18 + TypeScript 应用。
- **运行时：** Python `>=3.10,<3.14`；生产环境由 FastAPI 自动服务前端构建产物。

核心链路：

```text
Channel (IM message) -> ChannelManager -> AgentRunner -> QwenPawAgent (ReAct) -> Tools/Skills -> Response
```

## P3 阶段当前状态

- **权威路线图：** `docs/superpowers/specs/2026-05-09-enterprise-production-readiness-roadmap.md`。
- **P3-0 / P3-1 / P3-2 / P3-3 / P3-4 已完成：** 后续不要从上游同步、双入口打通、业务 Skills/MCP 承载、数据治理或运营管理闭环重新开工。
- **企业工作台：** `enterprise-admin/` 独立前端，不依赖 `console/src/*`。当前已覆盖 Dashboard、租户管理、入口配置、用户权限、能力管理、模型治理、业务追踪、Bad Case、验收测评、指标监控、配额中心、安全中心、备份恢复和诊断中心；策略中心和系统设置仍为阶段化开放。
- **当前 OpenSpec 状态：** `transform-qwenpaw-to-enterprise-platform` 已于 2026-05-16 归档到 `openspec/changes/archive/2026-05-16-transform-qwenpaw-to-enterprise-platform/`；归档收口时 baseline specs 严格校验通过。不要继续修改这个已归档 change，也不要使用 `openspec apply` 续做旧任务；新草稿或 active change 以 `openspec list --json` 的实时结果为准。
- **当前下一阶段：** 基于 `openspec/specs/` 的 baseline specs 开展新需求分析；新增功能、共享契约、身份 / 权限 / 会话 / 审计 / 租户边界变更仍需新建 OpenSpec change。若只是继续产品化已阶段化模块，先用 Superpowers 的 brainstorming / writing-plans 明确需求和验证边界。
- **P3-6 后续阶段：** 企业化验收与版本路线图仍后置，重点是业务测评、版本路线图、沟通材料、验收证据索引、问题清单和二期 backlog；自动问答回放、LLM 判分、跨租户聚合和报告导出仍属于后续验收增强。
- **后续组织口径：** 按企业平台产品模块和能力域推进，不再按早期分线职责描述拆分职责。
- **企业工作台能力矩阵：** `docs/superpowers/reports/2026-05-14-enterprise-admin-current-capability-matrix.md` 记录当前可用、MVP、后端已有未产品化和未开放模块。
- **Console 迁移矩阵：** `docs/superpowers/reports/2026-05-15-enterprise-admin-console-migration-matrix.md` 记录 Console 管理路由到 Enterprise Admin 能力域的替代、重构、监管、移除或阶段化结论。
- **P3-5 closeout / gate：** `docs/superpowers/reports/2026-05-12-p3-5-production-pilot-closeout.md`、`docs/superpowers/reports/2026-05-12-p3-5-release-gate.md` 和 `docs/superpowers/reports/2026-05-12-p3-acceptance-evidence-index.md` 记录平台基线、验证证据和残余风险。
- **验收路线：** `docs/superpowers/plans/2026-05-12-p3-6-enterprise-acceptance-roadmap.md`。

## 快速定位

| 需求类型 | 优先查看 |
| --- | --- |
| Agent 行为、工具调用、技能注入、记忆、MCP | `src/qwenpaw/agents/react_agent.py`、`src/qwenpaw/agents/tools/`、`src/qwenpaw/agents/skills_manager.py`、`src/qwenpaw/agents/memory/` |
| 请求执行、命令分发、Mission Mode、审批 | `src/qwenpaw/app/runner/`、`src/qwenpaw/agents/mission/` |
| IM 渠道接入 | `src/qwenpaw/app/channels/`、`src/qwenpaw/app/channels/base.py`、`src/qwenpaw/app/channels/registry.py` |
| 工作区、动态租户、WebChat 共享 Agent | `src/qwenpaw/app/workspace/`、`src/qwenpaw/app/agent_resolver.py`、`src/qwenpaw/tenancy/paths.py` |
| 企业运行时脊柱、请求上下文、存储、授权、审计、运行时扩展 | `src/qwenpaw/enterprise/`、`src/qwenpaw/enterprise/runtime.py`、`src/qwenpaw/enterprise/context.py`、`src/qwenpaw/enterprise/storage/`、`src/qwenpaw/enterprise/authz/`、`src/qwenpaw/enterprise/audit/`、`src/qwenpaw/enterprise/extensions/` |
| 业务 Skills / MCP 运行承载与调用追踪 | `src/qwenpaw/app/routers/wecom_tenant_config/feature_config.py`、`src/qwenpaw/app/runner/runner.py`、`src/qwenpaw/agents/mcp_tracer.py`、`src/qwenpaw/enterprise/audit/emit.py` |
| P3-4 运营管理、业务追踪和 Bad Case | `src/qwenpaw/app/routers/wecom_tenant_config/ops_insights.py`、`src/qwenpaw/app/routers/wecom_tenant_config/ops_schemas.py`、`console/src/pages/Control/WecomTenants/components/TenantOpsTab.tsx`、`console/src/pages/Control/WecomTenants/components/TenantTraceTable.tsx`、`console/src/pages/Control/WecomTenants/components/TenantBadCasePanel.tsx` |
| 企业工作台租户能力配置、业务追踪、Bad Case、验收测评、配额、安全、备份、诊断和指标 | `enterprise-admin/src/pages/AbilitiesPage.tsx`、`enterprise-admin/src/pages/BusinessTracePage.tsx`、`enterprise-admin/src/pages/BadCasesPage.tsx`、`enterprise-admin/src/pages/EvaluationPage.tsx`、`enterprise-admin/src/pages/MetricsPage.tsx`、`enterprise-admin/src/pages/QuotaPage.tsx`、`enterprise-admin/src/pages/SecurityPage.tsx`、`enterprise-admin/src/pages/BackupsPage.tsx`、`enterprise-admin/src/pages/DiagnosticsPage.tsx`、`enterprise-admin/src/features/platform-readiness/pageCompletenessModel.ts` |
| Console 用户/角色/租户绑定 | `src/qwenpaw/app/routers/auth.py`、`src/qwenpaw/app/auth.py`、`console/src/pages/Platform/Users/index.tsx` |
| 策略评估、配额与限流、可观测性、可靠性、API 安全、合规 | `src/qwenpaw/enterprise/policy/`、`src/qwenpaw/enterprise/quota/`、`src/qwenpaw/enterprise/observability/`、`src/qwenpaw/enterprise/reliability/`、`src/qwenpaw/enterprise/security/`、`src/qwenpaw/enterprise/compliance/` |
| 平台租户策略和模板 | `src/qwenpaw/tenancy/product_store.py`、`src/qwenpaw/app/routers/platform_tenancy.py` |
| FastAPI 路由 | `src/qwenpaw/app/routers/`、`src/qwenpaw/app/routers/__init__.py` |
| 配置模型和工作目录 | `src/qwenpaw/config/config.py`、`src/qwenpaw/constant.py` |
| LLM Provider | `src/qwenpaw/providers/`、`src/qwenpaw/providers/provider_manager.py` |
| 工具调用安全拦截 | `src/qwenpaw/security/tool_guard/` |
| Skill 安全扫描 | `src/qwenpaw/security/skill_scanner/` |
| Token 使用量统计 | `src/qwenpaw/token_usage/` |
| 备份恢复（含生产层） | `src/qwenpaw/backup/`、`src/qwenpaw/backup/production/` |
| Console 管理后台 | `console/src/` |
| WebChat 企业内部聊天 | `webchat/src/` |
| 企业工作台 | `enterprise-admin/src/` |
| 单元测试 | `tests/unit/` |

## 前端定位

- `console/` 是迁移期参考源码，不再作为长期管理后台或企业平台产品入口。
- `webchat/` 是企业内部聊天 UI：每个企业身份映射到一个 `wx_*` 动态租户工作区。
- `enterprise-admin/` 是企业工作台：独立于旧 Console，当前已覆盖 Dashboard、租户管理、入口配置、用户与权限、业务能力、模型治理、业务追踪、Bad Case 管理闭环、验收测评、指标监控只读摘要、配额中心、安全中心、备份恢复和诊断中心。
- 三个前端都使用 Ant Design 5、`antd-style`、axios 模块化 API、`i18next` 国际化。
- Enterprise Admin 重点路由：
  - `/enterprise-admin/dashboard`：企业运行总览。
  - `/enterprise-admin/tenants`：企微租户列表、创建、启动、停止、重启和详情。
  - `/enterprise-admin/users`：后台用户、角色绑定、租户绑定和只读权限矩阵。
  - `/enterprise-admin/abilities`：按租户查看 Skills/MCP，支持启停和 MCP 连接测试。
  - `/enterprise-admin/models`：租户模型治理，支持 active model 与 LLM routing 配置。
  - `/enterprise-admin/audit`：业务调用追踪，支持租户、能力类型/名称、入口、状态和错误原因筛选。
  - `/enterprise-admin/bad-cases`：Bad Case 管理闭环，支持租户选择、状态/分类筛选、负责人和备注编辑、状态流转。
  - `/enterprise-admin/evaluation`：验收测评，支持租户测评集、样例创建、人工执行记录、准确率报告和 Bad Case 转测评题。
  - `/enterprise-admin/metrics`：基于 `/api/metrics` 的 Prometheus 指标只读摘要。
  - `/enterprise-admin/quota`：Token Usage、默认限额和 `quota.denied` 审计视图。
  - `/enterprise-admin/security`：租户策略基线、权限拒绝审计和已具备审计契约的策略字段调整。
  - `/enterprise-admin/backups`：备份列表、生产策略、备份详情和低风险恢复演练。
  - `/enterprise-admin/diagnostics`：平台 readiness、企业运行时状态、租户 health 和入口配置诊断。
  - `/enterprise-admin/policies`、`/enterprise-admin/settings`：保留导航定位，阶段化开放，不包装成已交付能力。
- Console 重点路由：
  - `/platform`：平台租户总览。
  - `/platform/policies`：产品层成员权限和租户模板编辑。
  - `/platform/users`：Console 用户、角色和租户绑定管理。
  - `/wecom-tenants/monitoring`：只读诊断看板。
  - `/wecom-tenants/monitoring/:agentId`：单租户只读钻取页。
  - `/wecom-tenants`：租户管理、启动停止、配置、文件、Cron、运营总览、业务调用追踪和 Bad Case。

## WebChat 和租户注意点

- WebChat 是企业内部入口，不要恢复普通用户注册作为 fallback。
- `/api/webchat/*` 不走后台 Admin Auth；非公开 WebChat 路由必须从 WebChat session token 解析 `WebchatIdentity`。
- WebChat 和企业微信单聊 Bot 都应共享同一个 `wx_*` 动态租户 workspace。
- 动态租户配置读写 workspace 本地 `agent.json`，不要写回根配置 `config.agents.profiles`。
- WebChat 应设置 `request.state.agent_id`，下游通过统一 agent context 解析 Workspace。
- 不要重新引入 `request.state.webchat_workspace_dir`。
- `QWENPAW_TENANTS_ROOT`、默认 `WORKING_DIR/tenants`、`wx_*` 校验和租户路径构造统一由 `src/qwenpaw/tenancy/paths.py` 管理。

## 企业权限、Skills 和 MCP 注意点

- P3-2 明确使用 **RBAC**，不要重新引入 ABAC。角色和资源权限以 `src/qwenpaw/enterprise/authz/models.py` 为准。
- Skills / MCP 管理接口必须同时经过 RBAC 和租户边界校验；非 `platform_admin` 且没有明确 `tenant_id` 的 Console 管理请求当前应拒绝，避免跨租户管理。
- 租户级 Skills / MCP 配置继续写入 workspace-local `agent.json`，不要写回根配置 `config.agents.profiles`。
- MCP 审计追踪必须基于真实 tool 调用：`src/qwenpaw/agents/mcp_tracer.py` 通过 Toolkit middleware 记录实际调用，再由 `AgentRunner` 发出审计事件；不要按已加载 MCP client 批量补记成功或失败。
- P3-3 已把最小调用追踪深化为审计业务调用查询和治理数据闭环；P3-4 已提供 Console 产品化追踪视图和 Bad Case 标记/状态管理；企业工作台 Phase 2-3 已覆盖失败调用标记 Bad Case 和租户级 Bad Case 管理闭环；企业工作台 Phase 2-4 已覆盖租户测评集、人工执行记录、准确率报告和 Bad Case 转测评题。真实业务测评结论仍属于企业化验收阶段，HA、告警、回滚和多实例验证属于生产化保障。
- 正式立项口径以统一企业平台为准；不要把管理后台、员工入口和租户运行时实现成彼此独立的身份、权限或会话体系。
- Bad Case 依赖 append-only 审计事件持久化；`mark_bad_case` / `update_bad_case` 必须使用 strict 审计写入，不能在落库失败时返回成功。

## 常用命令

后端：

```bash
pip install -e ".[dev,full]"
qwenpaw init --defaults
qwenpaw app
pytest
make test-unit
make quick
make coverage-full
pre-commit run --all-files
```

前端：

```bash
cd console
npm install
npm run dev
npm run build
npm run format
npm run lint

cd webchat
npm install
npm run dev
npm run build
```

## 环境变量

- `QWENPAW_WORKING_DIR`：覆盖默认 `~/.qwenpaw` 工作目录。
- `QWENPAW_SECRET_DIR`：覆盖默认 `~/.qwenpaw.secret` 密钥目录。
- `COPAW_*`：历史前缀，会回退到对应 `QWENPAW_*`。
- `QWENPAW_STORAGE_BACKEND`：企业存储后端，默认 `json`；可设为 `sqlite` / `postgres`。
- `QWENPAW_DATABASE_URL`：SQL 存储连接串；未设置且使用 SQLite 时默认写入工作目录下的数据库文件。
- `QWENPAW_DB_POOL_SIZE` / `QWENPAW_DB_ECHO`：企业存储 SQLAlchemy 连接池大小和 SQL 日志开关。
- `QWENPAW_SANDBOX_ENABLED` / `QWENPAW_SANDBOX_GATEWAY_URL`：启用并预注册 sandbox-runtime 运行时扩展。
- `QWENPAW_AUTH_ENABLED`：启用 Console Admin Auth（生产环境必须显式开启）。
- `QWENPAW_AUTH_USERNAME` / `QWENPAW_AUTH_PASSWORD`：首次启用认证时自动注册初始管理员。
- `QWENPAW_QUOTA_ENABLED`：启用配额服务（`true`/`1`/`yes`）。
- `QWENPAW_REDIS_URL`：Redis 连接 URL，用于配额计数和死信队列。
- `QWENPAW_QUOTA_HTTP_PER_MINUTE`：HTTP 请求每分钟限制（默认 300）。
- `QWENPAW_QUOTA_LLM_TOKENS_PER_DAY`：LLM Token 每日限制（默认 1000000）。
- `QWENPAW_QUOTA_AUTH_LOGIN_PER_MINUTE`：登录每分钟限流（默认 20）。
- `QWENPAW_CORS_ORIGINS`：逗号分隔的 CORS 允许源；通配符 `*` 与 credentials 同时启用会被拒绝。
- `QWENPAW_CORS_ALLOW_CREDENTIALS`：是否允许 CORS credentials（默认 `true`）。
- `QWENPAW_LOG_FORMAT`：设为 `json` 启用结构化 JSON 日志（含企业上下文字段）。
- `QWENPAW_WEBCHAT_SSO_LOGIN_URL`：WebChat 企业 SSO 登录端点。
- `QWENPAW_WEBCHAT_SSO_COOKIE`：仅传给 SSO 登录请求的可选 Cookie。
- `QWENPAW_WEBCHAT_SESSION_SECRET`：生产环境必须显式设置的 WebChat session 签名密钥。
- `QWENPAW_WEBCHAT_QRCODE_*`：企业微信扫码登录相关配置。

## 临时产物

- 浏览器截图、调试截图、一次性验证图片和类似临时产物必须放在仓库根目录的 `.tmp/` 下。
- 不要把截图或其他临时验证文件直接写到项目根目录。
