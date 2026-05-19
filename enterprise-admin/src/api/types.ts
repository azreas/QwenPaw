export interface AuthStatus {
  authenticated: boolean
  username?: string
  role?: string
  authDisabled?: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  username: string
  role: string
}

export interface VersionInfo {
  version: string
  commit?: string
  buildTime?: string
}

export interface ReadyComponent {
  name: string
  ready?: boolean
  status?: "ok" | "degraded" | "down" | string
  message?: string
  details?: Record<string, unknown>
  latency_ms?: number
  latencyMs?: number
}

export interface ReadyStatus {
  ready: boolean
  components?: ReadyComponent[]
  checks?: {
    [key: string]: boolean | undefined
  }
}

export interface ReadinessSummary {
  status: string
  checks?: Record<string, unknown>
  blockers?: unknown[]
}

export interface EnterpriseReadiness {
  enabled?: boolean
  status: 'initializing' | 'ready' | 'degraded' | 'error' | 'blocked'
  features?: {
    authz?: boolean
    audit?: boolean
    quota?: boolean
    observability?: boolean
    policy?: boolean
    security?: boolean
    reliability?: boolean
    compliance?: boolean
  }
  storageBackend?: string
  checks?: Record<string, unknown>
}

export interface AuditEventItem {
  id: string
  event_type: string
  action: string
  outcome: string
  tenant_id?: string | null
  agent_id?: string | null
  actor_id?: string | null
  actor_type?: string | null
  resource_type?: string | null
  resource_id?: string | null
  request_id?: string | null
  trace_id?: string | null
  payload?: Record<string, unknown> | null
  created_at?: string | null
}

export interface AuditEventListResponse {
  events: AuditEventItem[]
  count: number
}

export interface PlatformSettingStatusItem {
  key: string
  label: string
  status: string
  source: string
  online_edit_supported: boolean
  value_redacted: boolean
  reason?: string
}

export interface PlatformSettingsSummary {
  frontend: {
    mode: string
    console_enabled: boolean
    root_entry: "enterprise-admin" | "console"
    console_access: "disabled" | "migration"
  }
  storage: {
    backend: string
    database_url_configured: boolean
    database_url_redacted: boolean
  }
  audit: {
    storage_available: boolean
    backend: string
  }
  compliance: {
    export_available: boolean
    formats: Array<"json" | "csv">
    reason?: string
  }
  controlled_switches: PlatformSettingStatusItem[]
}

export interface ComplianceExportRequest {
  tenant_id?: string
  actor_id?: string
  event_type?: string
  start_time?: string
  end_time?: string
  limit: number
  format: "json" | "csv"
}

export interface TokenUsageModelStats {
  model: string
  provider_id: string
  prompt_tokens: number
  completion_tokens: number
  call_count: number
}

export interface TokenUsageDateStats {
  prompt_tokens: number
  completion_tokens: number
  call_count: number
}

export interface TokenUsageSummary {
  total_prompt_tokens: number
  total_completion_tokens: number
  total_calls: number
  by_date: Record<string, TokenUsageDateStats>
}

export interface TokenUsageRecord {
  date: string
  provider_id: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  call_count: number
  agent_id: string
}

export interface QuotaLimitDefinition {
  dimension: string
  window: string
  max_value: number
  resource?: string
}

export interface QuotaConfigSummary {
  enabled: boolean
  redis_url_set: boolean
  default_limits: QuotaLimitDefinition[]
}

export interface TenantPolicy {
  policy_id: string
  display_name: string
  allow_model_switch: boolean
  allowed_models: string[]
  allow_skill_create: boolean
  allow_skill_upload_zip: boolean
  allow_skill_hub_import: boolean
  allow_tools: boolean
  allowed_tools: string[]
  allow_mcp: boolean
  allowed_mcp_transports: string[]
  allow_tasks: boolean
  max_cron_jobs: number
  min_cron_interval_minutes: number
  allow_task_run_now: boolean
  allow_task_tools: boolean
  task_timeout_seconds: number
  file_upload_limit_mb: number
  token_quota_monthly?: number | null
  advanced_config_enabled: boolean
}

export interface TenantPolicyListResponse {
  policies: TenantPolicy[]
}

export interface PlatformTenantRecord {
  tenant_id: string
  display_name: string
  agent_id: string
  status: string
  source: string
  policy_id: string
  template_id: string
  metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface PlatformTenantListResponse {
  tenants: PlatformTenantRecord[]
}

export interface DeleteResponse {
  deleted: boolean
}

export interface BackupScope {
  include_agents: boolean
  include_global_config: boolean
  include_secrets: boolean
  include_skill_pool: boolean
}

export interface BackupMeta {
  id: string
  name: string
  description: string
  created_at: string
  version: string
  scope: BackupScope
  agent_count: number
  qwenpaw_version: string
  system_info: Record<string, unknown>
}

export interface BackupDetail extends BackupMeta {
  workspace_stats: Record<string, Record<string, unknown>>
}

export interface BackupProductionPolicy {
  schedule: string
  retention_days: number
  remote_store: string
  integrity: string
}

export interface BackupDrillResult {
  ok?: boolean
  success?: boolean
  backup_id?: string
  sandbox_dir?: string
  restored_files?: number
  error?: string
}

/** 管理后台用户 */
export interface AdminUser {
  username: string
  roles: string[]
  tenant_id: string
  disabled: boolean
}

/** 用户列表响应 */
export interface UserListResponse {
  items: AdminUser[]
}

/** 创建管理后台用户请求 */
export interface CreateAdminUserRequest {
  username: string
  password: string
  roles: string[]
  tenant_id: string
}

/** 更新管理后台用户请求 */
export interface UpdateAdminUserRequest {
  roles?: string[]
  tenant_id?: string
  disabled?: boolean
}

/** 企微租户概要信息 */
export interface WecomTenantSummary {
  tenant_id: string
  agent_id: string
  workspace_dir: string
  exists: boolean
  initialized: boolean
  running: boolean
  updated_at?: string | null
  chat_count: number
  job_count: number
  source: 'workspace' | 'runtime' | string
}

/** 企微租户列表响应 */
export interface WecomTenantListResponse {
  tenants: WecomTenantSummary[]
}

/** 创建企微租户请求 */
export interface CreateWecomTenantRequest {
  tenant_id: string
  start?: boolean
}

export interface TenantHealthResponse {
  agent_id: string
  status: string
  checks: Record<string, unknown>
}

export interface TenantRuntimeFileInfo {
  filename: string
  size: number
  updated_at?: string | null
}

export interface TenantRuntimeFileListResponse {
  files: TenantRuntimeFileInfo[]
}

export interface TenantCronJob {
  id?: string | null
  name: string
  enabled: boolean
  schedule?: Record<string, unknown>
  task_type?: string
  text?: string
  dispatch?: Record<string, unknown>
}

export interface TenantEntryWecomConfig {
  enabled: boolean
  bot_id: string
  secret?: string | null
  secret_set?: boolean
  media_dir?: string | null
  welcome_text: string
  share_session_in_group: boolean
  max_reconnect_attempts: number
  streaming_enabled: boolean
  require_mention: boolean
  dm_policy: string
  group_policy: string
  allow_from: string[]
  deny_message: string
}

export interface TenantEntryWebchatConfig {
  enabled: boolean
  media_dir?: string | null
  user_data_dir?: string | null
  require_mention: boolean
  dm_policy: string
  group_policy: string
  allow_from: string[]
  deny_message: string
  session_secret_source?: string
  qrcode_config_source?: string
}

export interface TenantEntryConfig {
  wecom: TenantEntryWecomConfig
  webchat: TenantEntryWebchatConfig
}

export interface TenantEntryDiagnostics {
  agent_id: string
  status: string
  checks: Record<string, boolean>
  messages: string[]
}

export interface SkillInfo {
  name: string
  description: string
  source: string
  enabled: boolean
  installed: boolean
  installable: boolean
  channels: string[]
  tags: string[]
  requirements: string[]
  updated_at?: string | null
  last_call_at?: string | null
  last_call_status?: string | null
  last_error_reason?: string | null
  last_duration_ms?: number | null
}

export interface SkillOperationResponse {
  success: boolean
  name: string
  enabled?: boolean | null
  reason?: string | null
}

export interface SkillInstallRequest {
  skill_id: string
  overwrite?: boolean
}

export interface ToolInfo {
  name: string
  enabled: boolean
  description: string
  async_execution: boolean
  icon: string
}

export interface ToolAsyncExecutionRequest {
  async_execution: boolean
}

export interface MessageResponse {
  message: string
}

export interface MCPClientInfo {
  client_key: string
  name: string
  description: string
  enabled: boolean
  transport: string
  url: string
  command: string
  args: string[]
  cwd: string
  headers: Record<string, string>
  env: Record<string, string>
  last_call_at?: string | null
  last_call_status?: string | null
  last_error_reason?: string | null
  last_duration_ms?: number | null
  last_test_at?: string | null
  last_test_status?: string | null
  last_test_detail?: string | null
}

export interface MCPClientConfig {
  name: string
  description?: string
  enabled?: boolean
  transport?: string
  url?: string
  command?: string
  args?: string[]
  cwd?: string
  headers?: Record<string, string>
  env?: Record<string, string>
}

export interface MCPCreateRequest {
  client_key: string
  client: MCPClientConfig
}

export interface ModelSlotConfig {
  provider_id: string
  model: string
}

export interface AgentsLLMRoutingConfig {
  enabled: boolean
  mode: string
  local: ModelSlotConfig
  cloud?: ModelSlotConfig | null
}

export interface TenantTemplate {
  template_id: string
  display_name: string
  default_model?: string | null
  default_prompt_files: string[]
  default_skills: string[]
  default_tools: string[]
  default_task_templates: Record<string, unknown>[]
}

export interface TenantTemplateListResponse {
  templates: TenantTemplate[]
}

export interface TenantSecuritySettings {
  approval_level: string
  tool_guard_rules: Record<string, unknown>[]
}

export interface SystemPromptFilesResponse {
  files: string[]
}

export interface MCPConnectionTestResponse {
  client_key: string
  status:
    | 'ok'
    | 'auth_failed'
    | 'timeout'
    | 'unreachable'
    | 'invalid_config'
    | string
  detail: string
  duration_ms: number
}

export interface AbilityFailureSummary {
  ability_name: string
  ability_type: string
  count: number
  last_error: string
}

export interface OpsOverviewResponse {
  total_tenants: number
  running_tenants: number
  unhealthy_tenants: number
  business_calls_24h: number
  failed_calls_24h: number
  failure_rate: number
  entrypoints: Record<string, number>
  top_failed_abilities: AbilityFailureSummary[]
}

export interface BusinessTraceItem {
  id: string
  tenant_id: string
  agent_id: string
  session_id: string
  actor_id: string
  entrypoint: string
  ability_type: string
  ability_name: string
  duration_ms: number
  status: string
  error_reason: string
  request_id: string
  trace_id: string
  created_at: string
}

export interface TenantOpsSummaryResponse {
  tenant_id: string
  agent_id: string
  health_status: string
  last_activity_at?: string | null
  business_calls_24h: number
  failed_calls_24h: number
  recent_failures: BusinessTraceItem[]
}

export interface BusinessTraceListResponse {
  items: BusinessTraceItem[]
  total: number
}

export interface BusinessTraceQuery {
  ability_type?: 'skill' | 'mcp'
  ability_name?: string
  entrypoint?: string
  status?: string
  error_reason?: string
  limit?: number
}

export type BadCaseCategory =
  | 'platform_runtime'
  | 'data_quality'
  | 'permission_config'
  | 'product_experience'

export type BadCaseStatus =
  | 'open'
  | 'triaged'
  | 'transferred'
  | 'resolved'
  | 'ignored'

export interface BadCaseCreateRequest {
  source_audit_id: string
  source_request_id: string
  source_trace_id: string
  category: BadCaseCategory
  owner: string
  note: string
}

export interface BadCaseUpdateRequest {
  status?: BadCaseStatus
  category?: BadCaseCategory
  owner?: string
  note?: string
}

export interface BadCaseItem {
  case_id: string
  source_audit_id: string
  source_request_id: string
  source_trace_id: string
  category: string
  status: string
  owner: string
  note: string
  ability_type: string
  ability_name: string
  entrypoint: string
  created_at: string
  updated_at: string
}

export interface BadCaseListResponse {
  items: BadCaseItem[]
  total: number
}

export type EvalCategory =
  | 'indicator_query'
  | 'jargon_explain'
  | 'knowledge_retrieval'
  | 'permission_boundary'
  | 'product_experience'

export type EvalEntrypoint = 'webchat' | 'wecom_bot' | 'both'
export type EvalResult = 'correct' | 'partial' | 'wrong' | 'blocked'

export type IssueOwner =
  | 'data_quality'
  | 'platform_runtime'
  | 'permission_config'
  | 'product_experience'

export type EvalAction = 'fix' | 'transfer' | 'backlog' | 'close'

export interface EvalItem {
  case_id: string
  category: EvalCategory
  question: string
  expected: string
  entrypoint: EvalEntrypoint
  ability: string
  owner: string
  tags: string[]
}

export interface EvalItemInput {
  case_id?: string
  category: EvalCategory
  question: string
  expected: string
  entrypoint?: EvalEntrypoint
  ability?: string
  owner?: string
  tags?: string[]
}

export interface EvalDataset {
  id: string
  tenant_id: string
  name: string
  description: string
  items: EvalItem[]
  created_at: string
  updated_at: string
}

export interface CreateEvalDatasetRequest {
  name: string
  description?: string
  items?: EvalItemInput[]
}

export interface UpdateEvalDatasetRequest {
  name?: string
  description?: string
  items?: EvalItemInput[]
}

export interface AddEvalItemsRequest {
  items: EvalItemInput[]
}

export interface EvalDatasetListResponse {
  items: EvalDataset[]
  total: number
}

export interface EvalExecutionItem {
  case_id: string
  actual?: string
  trace_id?: string
  request_id?: string
  result: EvalResult
  issue_owner?: IssueOwner | null
  action?: EvalAction | null
  note?: string
  executed_at?: string
}

export interface EvalExecution {
  id: string
  tenant_id: string
  dataset_id: string
  items: EvalExecutionItem[]
  created_at: string
}

export interface CreateEvalExecutionRequest {
  dataset_id: string
  items: EvalExecutionItem[]
}

export interface EvalExecutionListResponse {
  items: EvalExecution[]
  total: number
}

export interface EvalExecutionQuery {
  dataset_id?: string
}

export interface AccuracyReport {
  dataset_id: string
  execution_id: string
  total: number
  executable: number
  correct: number
  partial: number
  wrong: number
  blocked: number
  correct_rate: number
  partial_rate: number
  issue_distribution: Record<string, number>
  created_at: string
}

export interface AcceptanceEvidenceExport {
  tenant_id: string
  agent_id: string
  dataset: EvalDataset
  execution: EvalExecution
  report: AccuracyReport
  exported_at: string
  evidence_version: string
}

export interface BadCaseToEvalRequest {
  case_ids: string[]
  dataset_id?: string | null
  dataset_name?: string
}

export interface BadCaseToEvalResult {
  dataset_id: string
  converted: number
  skipped: number
  items: EvalItem[]
}

export type PrometheusMetricType =
  | "counter"
  | "gauge"
  | "histogram"
  | "summary"
  | "untyped"

export interface MetricSample {
  name: string
  labels: Record<string, string>
  value: number
  raw: string
}

export interface MetricSummaryItem {
  name: string
  type: PrometheusMetricType
  help: string
  sampleCount: number
  latestValue?: number
}

export interface MetricsSummary {
  raw: string
  metrics: MetricSummaryItem[]
  samples: MetricSample[]
  metricCount: number
  sampleCount: number
  seriesCount: number
  typeCount: number
  unavailable: boolean
}
