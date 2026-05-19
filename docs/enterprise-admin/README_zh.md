# 企业工作台

企业工作台位于 `enterprise-admin/`，是内部企业部署的管理后台主入口。旧 `console/` 保留为 legacy/dev console，不作为企业后台主线继续扩展。

## 本地开发

```bash
npm.cmd install --prefix enterprise-admin
npm.cmd --prefix enterprise-admin run dev
```

默认开发端口是 `5175`，接口通过 Vite proxy 访问本地后端。

## 构建

```bash
npm.cmd --prefix enterprise-admin run build
```

构建产物输出到 `enterprise-admin/dist/`。

## 后端服务静态资源

```powershell
$env:QWENPAW_ENTERPRISE_ADMIN_STATIC_DIR="D:\claude-code\wx-agent\wyqpaw\enterprise-admin\dist"
qwenpaw app
```

企业部署默认从根路径 `/` 进入企业工作台；`/enterprise-admin/` 始终作为固定路径。

迁移期如需显式开启旧 Console 入口，可额外设置：

```powershell
$env:QWENPAW_FRONTEND_MODE="console"
$env:QWENPAW_CONSOLE_ENABLED="true"
$env:QWENPAW_CONSOLE_STATIC_DIR="D:\claude-code\wx-agent\wyqpaw\console\dist"
qwenpaw app
```

未显式开启 `QWENPAW_CONSOLE_ENABLED=true` 时，Console 不作为企业后台产品入口。

## 认证说明

企业工作台支持两种认证模式：

- **认证已启用**（`QWENPAW_AUTH_ENABLED=true`）：需要登录后才能访问工作台。
- **认证未启用**（默认）：工作台自动放行，Dashboard 会显示"认证未启用 / 已放行"，且右上角不显示"退出登录"按钮。

## 一期功能范围

### 已完成
- ✅ 独立前端工程搭建（Vite + TypeScript + React + Ant Design）
- ✅ 独立 API client 层（不依赖 console/）
- ✅ 登录页和 Auth 守卫
- ✅ 企业后台 Shell 布局和导航
- ✅ 运营总览 Dashboard（调用真实后端接口）
- ✅ 后端静态入口支持
- ✅ 完整的单元测试覆盖

### 后端接口调用

Dashboard 页面调用以下真实接口：
- `/api/auth/status` - 认证状态
- `/api/version` - 后端版本
- `/ready` - 服务就绪状态
- `/api/enterprise/readiness` - 企业运行时状态

## 当前能力范围

截至 2026-05-16，企业工作台已从早期 Phase 2 MVP 扩展为 Console 退场后的长期企业管理入口。当前页面状态以 `enterprise-admin/src/features/platform-readiness/pageCompletenessModel.ts` 为准：

| 页面 | 当前状态 | 说明 |
| --- | --- | --- |
| `/enterprise-admin/dashboard` | MVP 可用 | 企业运营总览和跨模块下钻入口。 |
| `/enterprise-admin/tenants` | 已可用 | 租户生命周期、详情、Agent 配置、入口诊断和运行资源查看。 |
| `/enterprise-admin/entry-config` | MVP 可用 | 租户级 WebChat / 企微入口配置和诊断。 |
| `/enterprise-admin/users` | MVP 可用 | 后台用户、角色绑定、租户绑定和只读权限矩阵。 |
| `/enterprise-admin/abilities` | MVP 可用 | 租户 Skills / MCP 启停、连接测试和调用状态。 |
| `/enterprise-admin/models` | MVP 可用 | 租户 active model 与 LLM routing 配置。 |
| `/enterprise-admin/audit` | MVP 可用 | 业务调用追踪、筛选、详情和 Bad Case 标记。 |
| `/enterprise-admin/bad-cases` | MVP 可用 | Bad Case 筛选、指派、备注和状态流转。 |
| `/enterprise-admin/evaluation` | MVP 可用 | 测评集、人工执行记录、准确率报告和 Bad Case 转测评题。 |
| `/enterprise-admin/metrics` | 只读 | 基于 `/api/metrics` 的 Prometheus 指标摘要和原始指标预览。 |
| `/enterprise-admin/quota` | MVP 可用 | Token Usage、默认限额和 `quota.denied` 审计视图。 |
| `/enterprise-admin/security` | MVP 可用 | 租户策略基线、权限拒绝审计和已具备审计契约的策略字段调整。 |
| `/enterprise-admin/backups` | MVP 可用 | 备份列表、生产策略、备份详情和低风险恢复演练。 |
| `/enterprise-admin/diagnostics` | MVP 可用 | 平台 readiness、企业运行时状态、租户 health 和入口配置诊断。 |
| `/enterprise-admin/policies` | 阶段化开放 | 保留策略中心导航定位，后续按契约开放。 |
| `/enterprise-admin/settings` | 阶段化开放 | 保留系统设置导航定位，后续按契约开放。 |

仍不包装成已交付能力的事项包括：Skills 安装 / 删除、MCP 创建 / 编辑 / 删除、自动问答回放、LLM 自动判分、跨租户准确率聚合、报告导出、完整告警配置、真实 restore / delete / import 按钮、评论、附件、通知、SLA 和工单系统同步。

## 二期能力拆分

二期按阶段接入企业管理功能：
- Phase 2-1：租户管理和用户权限。
- Phase 2-2：租户级 Skills/MCP 管理、审计日志和业务调用追踪。
- Phase 2-3：Bad Case 列表、标记和状态流转。
- Phase 2-4：测评集、人工执行记录、准确率报告和 Bad Case 转测评题。

测评集和准确率报告已在 Phase 2-4 作为 MVP 接入企业工作台，自动回放和导出不在本阶段范围内。

## Phase 2-1 能力

企业工作台 Phase 2-1 已接入两个核心运营页面：

- `/enterprise-admin/tenants`：企微租户列表、运行状态、创建租户、启动、停止、重启和详情查看。
- `/enterprise-admin/users`：后台用户列表、创建用户、角色绑定、租户绑定、禁用开关、内置角色目录和只读权限矩阵。

当前角色目录镜像后端 `src/qwenpaw/enterprise/authz/models.py` 的 `DEFAULT_ROLES`，本阶段不提供自定义角色配置。

## Phase 2-2 能力

企业工作台 Phase 2-2 接入租户能力配置和业务追踪 MVP：

- `/enterprise-admin/abilities`：按租户查看 Skills 和 MCP，支持启停 Skills、启停 MCP、MCP 连接测试，并展示调用状态。
- `/enterprise-admin/audit`：业务调用追踪页面，支持租户选择、24h 运营摘要、能力类型/名称/入口/状态/错误原因筛选和调用证据表格。

本阶段不提供 Skills 安装删除、MCP 创建编辑删除、Bad Case 标记流转和通用审计日志搜索；这些能力保留给后续阶段独立实现。

## Phase 2-3 能力

企业工作台 Phase 2-3 接入 Bad Case 管理闭环 MVP：

- `/enterprise-admin/audit`：失败调用支持直接标记 Bad Case，提交内容包括分类、负责人和备注。
- `/enterprise-admin/bad-cases`：按租户查看 Bad Case，支持状态/分类筛选、负责人和备注编辑、状态流转。

Bad Case 仍以后端 append-only 审计事件为权威存储；标记或更新时如果审计写入失败，页面必须提示未保存，不允许前端伪造成功。

本阶段不提供测评集、准确率报告、Bad Case 转测评集、评论流、附件、通知、SLA 或工单系统同步；这些验收能力已在 Phase 2-4 以 MVP 形式继续接入。

## Phase 2-4 能力

企业工作台 Phase 2-4 接入验收测评 MVP：

- `/enterprise-admin/evaluation`：按租户维护测评集，支持从平台样例创建测评集。
- `/enterprise-admin/evaluation`：支持人工录入执行结果，并基于后端准确率模型查看正确率、部分正确率、阻塞数和问题归属分布。
- `/enterprise-admin/evaluation`：支持从 Bad Case 勾选转入已有测评集或新测评集，形成运营问题到验收题目的闭环。

本阶段不做自动问答回放、大模型自动判分、PDF/Excel 导出或跨租户汇总；执行结果由管理员人工录入，准确率由后端 `/api/evaluation/tenants/{agent_id}/executions/{execution_id}/report` 计算。

## Console 退场后新增能力

2026-05-16 后，企业工作台继续补齐 Console 退场基础闭环和运行保障入口：

- `/enterprise-admin/entry-config`：产品化租户入口配置和诊断。
- `/enterprise-admin/models`：产品化租户模型治理和路由配置。
- `/enterprise-admin/metrics`：将原未开放模块升级为只读 Prometheus 指标摘要。
- `/enterprise-admin/quota`：产品化 Token Usage、默认配额和超限审计只读视图。
- `/enterprise-admin/security`：产品化租户策略基线、权限拒绝审计，并对已有审计契约支持的字段开放受控写入。
- `/enterprise-admin/backups`：产品化备份列表、策略、详情和低风险恢复演练；真实恢复、删除和导入仍阶段化。
- `/enterprise-admin/diagnostics`：产品化 readiness、企业运行时状态、租户健康和入口诊断。

企业部署默认从根路径 `/` 进入 Enterprise Admin。Console 仅作为迁移期参考入口，必须显式设置 `QWENPAW_CONSOLE_ENABLED=true` 才会暴露。
