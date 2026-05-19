export type EnterprisePageKey =
  | "dashboard"
  | "tenants"
  | "entryConfig"
  | "users"
  | "abilities"
  | "models"
  | "policies"
  | "audit"
  | "badCases"
  | "evaluation"
  | "metrics"
  | "quota"
  | "security"
  | "backups"
  | "diagnostics"
  | "settings"

export type PageCompletenessStatus =
  | "available"
  | "mvp"
  | "read-only"
  | "staged"

export interface PageCompletenessDefinition {
  key: EnterprisePageKey
  title: string
  status: PageCompletenessStatus
  positioning: string
  completeWhen: string
  currentWorkflow: string[]
  backendContracts: string[]
  rbacBoundary: string
  tenantBoundary: string
  auditEvents: string[]
  pageStates: string[]
  gaps: string[]
  stagedCapabilities: string[]
  consoleExitRelation: string
}

type PageCompletenessMap = {
  [K in EnterprisePageKey]: PageCompletenessDefinition & { key: K }
}

export const ENTERPRISE_PAGE_COMPLETENESS: PageCompletenessMap = {
  dashboard: {
    key: "dashboard",
    title: "企业运营总览",
    status: "mvp",
    positioning: "面向平台管理员的企业运行与验收入口概览页。",
    completeWhen: "核心运营指标可在单页完成浏览与下钻，跨模块状态能支撑试点验收巡检。",
    currentWorkflow: [
      "查看总览卡片后进入租户、追踪、Bad Case 与测评页面继续处理。",
    ],
    backendContracts: [
      "依赖企业运行概览与各业务聚合接口输出稳定统计。",
    ],
    rbacBoundary: "仅平台管理角色可见整体视角。",
    tenantBoundary: "聚合视角不泄露租户敏感明细。",
    auditEvents: ["记录概览访问与关键下钻动作。"],
    pageStates: ["加载中", "聚合成功", "部分数据缺失", "空态"],
    gaps: ["租户聚合、业务追踪聚合、Bad Case 聚合、测评聚合仍需补齐"],
    stagedCapabilities: ["跨页筛选条件联动", "聚合口径说明"],
    consoleExitRelation: "替代 /platform 和 /agent-stats 的企业运营总览语义。",
  },
  tenants: {
    key: "tenants",
    title: "租户管理",
    status: "available",
    positioning: "统一承载企业租户生命周期、状态、入口配置和租户 Agent 配置。",
    completeWhen: "租户列表、创建、启停、详情、Agent 配置、入口诊断和运行资源在单页闭环。",
    currentWorkflow: ["从租户列表进入详情，查看平台模板和 tenant-local Agent 配置后继续能力、追踪和测评操作。"],
    backendContracts: ["依赖租户管理、平台模板、tenant-local system prompts/security、运行状态、入口配置、能力、模型、文件、记忆和 Cron 接口。"],
    rbacBoundary: "按平台管理员与租户管理员角色控制。",
    tenantBoundary: "租户级操作必须绑定明确 tenant_id。",
    auditEvents: ["记录创建、启动、停止、重启与配置变更。"],
    pageStates: ["列表", "详情抽屉", "执行中", "失败提示"],
    gaps: ["平台模板应用、导入 dry-run 和更细诊断聚合仍阶段化开放。"],
    stagedCapabilities: ["批量运维", "租户模板应用", "导入 dry-run"],
    consoleExitRelation: "替代 /wecom-tenants，并吸收 /channels 的租户入口配置语义。",
  },
  entryConfig: {
    key: "entryConfig",
    title: "入口配置",
    status: "mvp",
    positioning: "承接 WebChat、企微 Bot、回调、凭证和会话设置的租户级入口治理。",
    completeWhen: "入口凭证、回调诊断、可信来源和会话设置可按租户查看并受控写入。",
    currentWorkflow: ["选择租户后维护企微 Bot 与 WebChat 租户入口配置，并运行入口诊断。"],
    backendContracts: ["依赖租户 entry-config 读取、更新和诊断接口。"],
    rbacBoundary: "入口配置写操作需限定在平台管理员或授权租户管理员。",
    tenantBoundary: "入口配置必须绑定明确租户，写入 tenant-local agent.json 或托管存储。",
    auditEvents: ["记录入口配置更新、诊断测试和失败原因。"],
    pageStates: ["租户选择", "表单加载", "保存中", "诊断结果", "失败提示"],
    gaps: ["WebChat SSO、二维码和 session secret 仍由平台环境变量管理。"],
    stagedCapabilities: ["WebChat SSO 配置", "二维码平台配置", "回调连通性外部探测"],
    consoleExitRelation: "重构 /channels 和 /wecom-tenants 配置页的企业入口配置语义。",
  },
  users: {
    key: "users",
    title: "用户与权限",
    status: "mvp",
    positioning: "统一管理后台用户、角色绑定与租户授权关系。",
    completeWhen: "用户、角色、租户绑定与只读权限矩阵在同一产品域可见。",
    currentWorkflow: ["维护账号绑定后返回租户或能力页继续验收。"],
    backendContracts: ["依赖用户、角色、租户绑定和 RBAC 查询接口。"],
    rbacBoundary: "仅授权管理员可调整用户与角色。",
    tenantBoundary: "租户绑定操作必须落在明确租户边界内。",
    auditEvents: ["记录角色绑定、解绑和租户授权变更。"],
    pageStates: ["列表", "编辑弹窗", "只读矩阵", "空态"],
    gaps: ["细粒度拒绝原因展示仍可增强。"],
    stagedCapabilities: ["权限拒绝审计", "token 失效策略说明", "角色引用检查"],
    consoleExitRelation: "替代 /platform/users。",
  },
  abilities: {
    key: "abilities",
    title: "能力管理",
    status: "mvp",
    positioning: "按租户统一管理 Skills、MCP 与后续能力目录。",
    completeWhen: "租户级能力启停、连接测试与基础说明可在一个入口完成。",
    currentWorkflow: ["选择租户后查看能力列表、执行连接测试并调整状态。"],
    backendContracts: ["依赖租户能力列表、启停与 MCP 测试接口。"],
    rbacBoundary: "能力管理受 RBAC 与租户权限双重约束。",
    tenantBoundary: "所有配置写入 workspace-local agent.json。",
    auditEvents: ["记录能力启停、测试连接和配置变更。"],
    pageStates: ["租户切换", "列表", "测试中", "失败提示"],
    gaps: ["能力来源与依赖关系展示仍需继续补足。"],
    stagedCapabilities: [
      "能力目录",
      "Tools",
      "Skill 安装",
      "MCP 创建编辑",
      "安全扫描",
      "批量授权",
    ],
    consoleExitRelation: "重构 /skills、/skill-pool、/tools、/mcp 和 /acp。",
  },
  models: {
    key: "models",
    title: "模型治理",
    status: "mvp",
    positioning: "承接平台模型池、租户模型授权和模型路由治理。",
    completeWhen: "平台模型库存、租户授权、路由策略和审计记录形成管理闭环。",
    currentWorkflow: ["选择租户后维护 active model 与 LLM routing。"],
    backendContracts: ["依赖租户 active model 与 llm-routing 读写接口。"],
    rbacBoundary: "模型授权和路由调整仅限授权管理员。",
    tenantBoundary: "租户模型授权与路由需显式绑定 tenant_id。",
    auditEvents: ["记录模型配置和路由变更。"],
    pageStates: ["租户选择", "表单加载", "保存中", "失败提示"],
    gaps: ["平台模型库存、模型发现和跨租户授权矩阵仍阶段化开放。"],
    stagedCapabilities: ["平台模型库存", "模型发现", "跨租户授权矩阵", "连通性测试"],
    consoleExitRelation: "重构 /models 为企业平台模型治理模块。",
  },
  policies: {
    key: "policies",
    title: "策略中心",
    status: "mvp",
    positioning: "平台级承载成员策略、租户模板与影响范围治理的配置中心。",
    completeWhen: "平台策略与租户模板 CRUD、影响范围预览和删除保护可在 Enterprise Admin 原生闭环中稳定使用。",
    currentWorkflow: [
      "平台管理员统一查看策略与模板列表，维护平台默认策略并结合租户引用关系确认影响范围后执行增删改。",
    ],
    backendContracts: [
      "依赖 /platform/tenancy/policies、/platform/tenancy/templates 和 /platform/tenancy/tenants 的读写契约提供策略、模板与租户引用数据。",
    ],
    rbacBoundary: "仅平台管理员可访问并修改平台级策略、模板和引用关系。",
    tenantBoundary: "策略与模板为平台级配置，但影响范围预览和引用统计必须基于明确 tenant_id 展示，不允许租户管理员跨租户写入。",
    auditEvents: [
      "记录策略保存、模板保存、策略删除、模板删除与引用范围变更确认。",
    ],
    pageStates: ["列表加载", "表单编辑", "保存中", "删除保护提示", "空态", "失败提示"],
    gaps: [
      "发布审批、版本回滚、批量应用和变更历史仍未产品化，当前以直接 CRUD 和影响范围预览支撑 MVP。",
    ],
    stagedCapabilities: ["发布审批", "版本回滚", "批量应用", "变更历史"],
    consoleExitRelation: "Enterprise Admin 原生承接平台策略与租户模板治理，不再依赖 Console 兜底。",
  },
  audit: {
    key: "audit",
    title: "业务追踪",
    status: "mvp",
    positioning: "统一查看业务调用追踪、失败诊断与上下文过滤。",
    completeWhen: "租户级追踪查询、过滤、诊断与 Bad Case 标记稳定可用。",
    currentWorkflow: ["筛选追踪记录，定位失败，再联动到 Bad Case 或测评。"],
    backendContracts: ["依赖审计追踪查询、详情与 Bad Case 标记接口。"],
    rbacBoundary: "查看与标记动作受 RBAC 控制。",
    tenantBoundary: "查询结果必须受 tenant_id 与入口边界约束。",
    auditEvents: ["记录追踪查询、详情查看和标记操作。"],
    pageStates: ["列表", "筛选", "详情面板", "失败空态"],
    gaps: ["更细的诊断预设与跨页回流仍可继续增强。"],
    stagedCapabilities: ["诊断剧本", "失败模式聚类"],
    consoleExitRelation: "吸收 /sessions、/debug、/wecom-tenants/monitoring 的追踪诊断语义。",
  },
  badCases: {
    key: "badCases",
    title: "Bad Case",
    status: "mvp",
    positioning: "承载租户级问题闭环、指派、状态流转与备注沉淀。",
    completeWhen: "Bad Case 标记、筛选、认领、流转与转测评路径稳定可用。",
    currentWorkflow: ["从追踪页标记后进入 Bad Case 页完成处理闭环。"],
    backendContracts: ["依赖 strict 审计写入与 Bad Case 查询更新接口。"],
    rbacBoundary: "编辑动作需受角色权限控制。",
    tenantBoundary: "所有记录必须绑定原始租户与审计事件。",
    auditEvents: ["记录标记、更新状态、备注与负责人变更。"],
    pageStates: ["列表", "筛选", "编辑侧栏", "空态"],
    gaps: ["批量治理与趋势分析仍可扩展。"],
    stagedCapabilities: ["批量处理", "治理趋势"],
    consoleExitRelation: "替代 Console 中租户运营 Bad Case 扩展。",
  },
  evaluation: {
    key: "evaluation",
    title: "验收测评",
    status: "mvp",
    positioning: "企业工作台原生承载测评集、执行记录与准确率报告。",
    completeWhen: "租户级测评集、执行记录、报告与 Bad Case 转题稳定可用。",
    currentWorkflow: ["维护测评集，执行人工记录，查看准确率并回流 Bad Case。"],
    backendContracts: ["依赖测评集、执行记录、报告与 Bad Case 转换接口。"],
    rbacBoundary: "测评维护与执行记录需按角色分权。",
    tenantBoundary: "所有测评数据需绑定租户并隔离访问。",
    auditEvents: ["记录样例创建、执行记录、报告查看与转题操作。"],
    pageStates: ["列表", "样例编辑", "执行记录", "报告"],
    gaps: ["自动化执行链路与更丰富报告仍在后续阶段。"],
    stagedCapabilities: ["自动问答回放", "批量回归执行", "报告对比"],
    consoleExitRelation: "Enterprise Admin 原生验收模块，不回退到 Console。",
  },
  metrics: {
    key: "metrics",
    title: "指标监控",
    status: "read-only",
    positioning: "基于 /api/metrics 的 Prometheus 指标只读摘要页，用于试运行巡检和问题定位。",
    completeWhen: "Prometheus 原始文本、基础摘要、空态说明和只读预览在单页稳定可读，且不误导为完整监控中心。",
    currentWorkflow: ["读取原始指标文本，查看摘要卡片和指标表，再结合原始指标预览做只读核对。"],
    backendContracts: ["依赖 /api/metrics 暴露稳定的 Prometheus text exposition 文本。"],
    rbacBoundary: "指标范围需受平台与租户权限控制。",
    tenantBoundary: "跨租户聚合与单租户下钻需要隔离。",
    auditEvents: ["记录指标页面访问，后续补充导出和告警治理操作。"],
    pageStates: ["加载中", "摘要成功", "Observability 未启用", "暂无可用指标"],
    gaps: ["趋势图、告警配置、导出能力和跨租户下钻仍未开放。"],
    stagedCapabilities: ["告警配置", "趋势图", "导出分析", "跨租户下钻"],
    consoleExitRelation: "以 Enterprise Admin 原生只读摘要承接基础指标巡检，不回退到 Console 指标占位页。",
  },
  quota: {
    key: "quota",
    title: "配额中心",
    status: "mvp",
    positioning: "管理 Token 用量、默认配额配置和超限审计视图。",
    completeWhen: "Token 用量、默认限额、超限审计、调整、告警与回溯可在 Enterprise Admin 闭环。",
    currentWorkflow: ["查看 Token Usage 聚合、默认限额和 quota.denied 审计事件。"],
    backendContracts: ["依赖 token-usage、quota summary 和 audit events 只读接口。"],
    rbacBoundary: "配额变更仅限授权管理员。",
    tenantBoundary: "配额需区分全局与租户维度。",
    auditEvents: ["需记录配额调整、触发与恢复。"],
    pageStates: ["用量总览", "默认限额", "超限审计", "失败提示"],
    gaps: ["配额调整、超限处置和告警策略仍需写契约与审计闭环。"],
    stagedCapabilities: ["配额调整", "超限告警", "历史回放", "租户级覆盖策略"],
    consoleExitRelation: "后续替代 Console/后端分散的配额入口。",
  },
  security: {
    key: "security",
    title: "安全中心",
    status: "mvp",
    positioning: "集中展示租户策略基线、权限拒绝审计与安全治理入口。",
    completeWhen: "安全检查、策略配置、权限拒绝复盘、问题处置与审计入口形成统一闭环。",
    currentWorkflow: ["查看租户策略基线、调整已有审计契约支持的配额字段，并复盘 authz.denied 事件。"],
    backendContracts: ["依赖 platform tenancy policies 和 audit events 接口。"],
    rbacBoundary: "安全域操作需更严格授权。",
    tenantBoundary: "安全事件需要按租户与平台分层查看。",
    auditEvents: ["需记录扫描执行、策略变更与告警处理。"],
    pageStates: ["策略列表", "权限拒绝审计", "保存中", "失败提示"],
    gaps: ["审批处置、blocked history 清理和完整安全策略编排仍阶段化开放。"],
    stagedCapabilities: ["安全扫描", "告警看板", "基线检查", "审批处置", "blocked history 清理"],
    consoleExitRelation: "后续承接分散的安全治理入口。",
  },
  backups: {
    key: "backups",
    title: "备份恢复",
    status: "mvp",
    positioning: "承接租户与平台备份、恢复演练和风险确认流程。",
    completeWhen: "备份列表、恢复演练、风险确认、审计和结果查询形成闭环。",
    currentWorkflow: ["查看备份列表、生产备份策略、备份详情并执行低风险恢复演练。"],
    backendContracts: ["依赖 backups list/detail、production policy、restore drill、确认与审计接口。"],
    rbacBoundary: "恢复和删除类操作必须限定高权限管理员并要求确认。",
    tenantBoundary: "租户备份、恢复和导出必须绑定租户边界，平台级备份需单独授权。",
    auditEvents: ["记录恢复演练、真实恢复、删除、导入、确认缺失和失败原因。"],
    pageStates: ["备份列表", "生产策略", "备份详情", "恢复演练", "高风险提示"],
    gaps: ["Enterprise Admin 暂不开放真实 restore、delete、import 按钮，仅保留后端确认与审计契约。"],
    stagedCapabilities: ["真实恢复", "备份删除", "备份导入"],
    consoleExitRelation: "阶段化重构 /backups 的安全备份恢复语义。",
  },
  diagnostics: {
    key: "diagnostics",
    title: "诊断中心",
    status: "mvp",
    positioning: "集中承载 readiness、租户配置诊断、日志线索和安全测试链接。",
    completeWhen: "平台 readiness、租户诊断、依赖状态和安全测试入口可统一查询。",
    currentWorkflow: ["查看 /ready、enterprise readiness、组件状态、租户 health 和入口配置诊断。"],
    backendContracts: ["依赖 /ready、enterprise readiness、tenant health 和 entry diagnostics 接口。"],
    rbacBoundary: "诊断信息按平台管理员和租户管理员分层展示。",
    tenantBoundary: "租户诊断必须按租户隔离，跨租户聚合不得泄露敏感配置。",
    auditEvents: ["需记录诊断查看、测试链接触发和失败原因。"],
    pageStates: ["平台 readiness", "组件状态", "企业化检查", "租户诊断", "失败提示"],
    gaps: ["日志摘要、安全测试链接和跨租户诊断报告仍等待后端契约。"],
    stagedCapabilities: ["日志摘要", "安全测试链接", "跨租户诊断报告"],
    consoleExitRelation: "重构 /debug、/wecom-tenants/monitoring 和运行诊断入口。",
  },
  settings: {
    key: "settings",
    title: "系统设置",
    status: "mvp",
    positioning: "平台级只读设置摘要、默认入口状态、Console 迁移状态和合规导出入口。",
    completeWhen: "平台管理员可查看脱敏系统状态、识别高风险设置为不支持在线修改，并可发起合规审计导出。",
    currentWorkflow: ["查看只读平台配置摘要、确认 Console 迁移状态、按筛选条件导出合规审计。"],
    backendContracts: ["依赖 /api/settings/platform-summary 和 /api/compliance/audit/export。"],
    rbacBoundary: "系统设置 MVP 仅限 platform_admin 访问。",
    tenantBoundary: "租户字段仅作为合规导出筛选，不提供租户配置编辑。",
    auditEvents: ["记录 compliance.exported；在线 settings.update 不在本期范围。"],
    pageStates: ["加载中", "摘要成功", "摘要降级", "无权访问", "不支持在线修改", "导出中", "导出成功", "导出失败"],
    gaps: ["在线修改、默认入口切换、Console 开关修改和配置回滚仍需独立 OpenSpec change。"],
    stagedCapabilities: ["在线修改", "默认入口切换", "Console 开关修改", "配置回滚"],
    consoleExitRelation: "以 Enterprise Admin 原生系统设置 MVP 承接平台设置查看和合规导出，不回退到 Console。",
  },
}

export function getPageCompleteness(
  key: EnterprisePageKey | string,
): PageCompletenessDefinition | undefined {
  if (!Object.prototype.hasOwnProperty.call(ENTERPRISE_PAGE_COMPLETENESS, key)) {
    return undefined
  }

  return ENTERPRISE_PAGE_COMPLETENESS[key as EnterprisePageKey]
}

export function getPageCompletenessStatusTag(
  status: PageCompletenessStatus,
): { color: string; text: string } {
  const statusMap: Record<PageCompletenessStatus, { color: string; text: string }> =
    {
      available: { color: "green", text: "已可用" },
      mvp: { color: "blue", text: "MVP 可用" },
      "read-only": { color: "purple", text: "只读" },
      staged: { color: "orange", text: "阶段化开放" },
    }
  return statusMap[status]
}
