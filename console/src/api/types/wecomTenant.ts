import type { AgentStatsSummary } from "./agentStats";
import type { CronJobSpecInput, CronJobSpecOutput } from "./cronjob";
import type { TokenUsageSummary } from "./tokenUsage";

export interface WecomTenantSummary {
  tenant_id: string;
  agent_id: string;
  workspace_dir: string;
  exists: boolean;
  initialized: boolean;
  running: boolean;
  updated_at?: string | null;
  chat_count: number;
  job_count: number;
  source: "workspace" | "runtime";
}

export interface WecomTenantListResponse {
  tenants: WecomTenantSummary[];
}

export interface CreateWecomTenantRequest {
  tenant_id: string;
  start?: boolean;
}

export interface WecomMessageResponse {
  message: string;
}

export interface WecomTenantDashboardTrendItem {
  date: string;
  tokens: number;
  messages: number;
  active_tenants: number;
}

export interface WecomTenantDashboardResponse {
  total_tenants: number;
  running_tenants: number;
  stopped_tenants: number;
  broken_tenants: number;
  total_tokens: number;
  total_chats: number;
  total_messages: number;
  daily_trend: WecomTenantDashboardTrendItem[];
}

export type WecomTenantHealthStatus = "healthy" | "degraded" | "unhealthy";

export interface WecomTenantHealthResponse {
  agent_id: string;
  status: WecomTenantHealthStatus;
  checks: Record<string, unknown>;
}

export interface WecomAllTenantHealthResponse {
  tenants: WecomTenantHealthResponse[];
}

export interface WecomModelSlot {
  provider_id: string;
  model: string;
}

export type WecomLlmRoutingConfig = Record<string, unknown>;

export interface WecomTenantTool {
  name: string;
  enabled: boolean;
  description: string;
  async_execution: boolean;
  icon: string;
}

export interface WecomToolAsyncExecutionRequest {
  async_execution: boolean;
}

export interface WecomTenantSkill {
  name: string;
  description: string;
  source: string;
  enabled: boolean;
  installed?: boolean;
  installable?: boolean;
  channels?: string[];
  tags?: string[];
  requirements?: string[];
  updated_at?: string | null;
  last_call_at?: string | null;
  last_call_status?: string | null;
  last_error_reason?: string | null;
  last_duration_ms?: number | null;
}

export interface WecomTenantSkillInstallRequest {
  skill_id: string;
  overwrite?: boolean;
}

export interface WecomTenantSkillOperationResponse {
  success: boolean;
  name: string;
  enabled?: boolean | null;
  reason?: string | null;
}

export type WecomMcpTransport = "stdio" | "streamable_http" | "sse";

export interface WecomTenantMcpClient {
  client_key: string;
  name: string;
  description: string;
  enabled: boolean;
  transport: WecomMcpTransport;
  url: string;
  command: string;
  args: string[];
  cwd: string;
  headers: Record<string, string>;
  env: Record<string, string>;
  last_call_at?: string | null;
  last_call_status?: string | null;
  last_error_reason?: string | null;
  last_duration_ms?: number | null;
  last_test_at?: string | null;
  last_test_status?: string | null;
  last_test_detail?: string | null;
}

export interface WecomTenantMcpCreateRequest {
  client_key: string;
  client: Omit<WecomTenantMcpClient, "client_key">;
}

export interface WecomTenantSecurityRule {
  id?: string;
  tools?: string[];
  params?: string[];
  category?: string;
  severity?: string;
  patterns?: string[];
  exclude_patterns?: string[];
  description?: string;
  remediation?: string;
  [key: string]: unknown;
}

export interface WecomTenantSecuritySettings {
  approval_level: string;
  tool_guard_rules: WecomTenantSecurityRule[];
}

export interface WecomTenantSystemPrompts {
  files: string[];
}

export interface WecomTenantChatListParams {
  page?: number;
  page_size?: number;
  channel?: string;
}

export interface WecomTenantGlobalChatListParams
  extends WecomTenantChatListParams {
  agent_ids?: string;
}

export interface WecomTenantStatsParams {
  start_date?: string;
  end_date?: string;
  agent_ids?: string;
  model?: string;
  provider?: string;
}

export interface WecomTenantChatListResponse {
  items: Record<string, unknown>[];
  page: number;
  page_size: number;
  total: number;
}

export interface WecomTenantFileInfo {
  filename: string;
  size: number;
  updated_at?: string | null;
}

export interface WecomTenantFileListResponse {
  files: WecomTenantFileInfo[];
}

export interface WecomTenantFileContent {
  filename: string;
  content: string;
}

export interface WecomTenantOperationResult {
  agent_id: string;
  success: boolean;
  error?: string | null;
}

export interface WecomTenantBatchOperationRequest {
  agent_ids?: string[];
  all?: boolean;
}

export interface WecomTenantBatchOperationResponse {
  results: WecomTenantOperationResult[];
}

export interface WecomTenantDeleteRequest {
  confirm: boolean;
}

export type WecomTenantTokenUsage = TokenUsageSummary;
export type WecomTenantAgentStats = AgentStatsSummary;
export type WecomTenantCronJobInput = CronJobSpecInput;
export type WecomTenantCronJob = CronJobSpecOutput;

// ── 运营管理类型 ──────────────────────────────────────────────────────────

export interface WecomTenantAbilityFailure {
  ability_name: string;
  ability_type: string;
  count: number;
  last_error: string;
}

export interface WecomTenantOpsOverview {
  total_tenants: number;
  running_tenants: number;
  unhealthy_tenants: number;
  business_calls_24h: number;
  failed_calls_24h: number;
  failure_rate: number;
  entrypoints: Record<string, number>;
  top_failed_abilities: WecomTenantAbilityFailure[];
}

export interface WecomTenantBusinessTrace {
  id: string;
  tenant_id: string;
  agent_id: string;
  session_id: string;
  actor_id: string;
  entrypoint: string;
  ability_type: string;
  ability_name: string;
  duration_ms: number;
  status: string;
  error_reason: string;
  request_id: string;
  trace_id: string;
  created_at: string;
}

export interface WecomTenantOpsSummary {
  tenant_id: string;
  agent_id: string;
  health_status: string;
  last_activity_at: string | null;
  business_calls_24h: number;
  failed_calls_24h: number;
  recent_failures: WecomTenantBusinessTrace[];
}

export interface WecomTenantBadCase {
  case_id: string;
  source_audit_id: string;
  source_request_id: string;
  source_trace_id: string;
  category: string;
  status: string;
  owner: string;
  note: string;
  ability_type: string;
  ability_name: string;
  entrypoint: string;
  created_at: string;
  updated_at: string;
}

export interface WecomTenantBadCaseListResponse {
  items: WecomTenantBadCase[];
  total: number;
}

export interface BadCaseCreateRequest {
  source_audit_id: string;
  source_request_id?: string;
  source_trace_id?: string;
  category:
    | "platform_runtime"
    | "data_quality"
    | "permission_config"
    | "product_experience";
  owner?: string;
  note?: string;
}

export interface BadCaseUpdateRequest {
  status?: "open" | "triaged" | "transferred" | "resolved" | "ignored";
  category?:
    | "platform_runtime"
    | "data_quality"
    | "permission_config"
    | "product_experience";
  owner?: string;
  note?: string;
}
