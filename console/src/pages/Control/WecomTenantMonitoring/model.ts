import type { AgentSummary } from "../../../api/types/agents";
import type { TokenUsageSummary } from "../../../api/types/tokenUsage";
import type {
  WecomTenantHealthResponse,
  WecomTenantStatsParams,
  WecomTenantSummary,
} from "../../../api/types/wecomTenant";

// ---- 健康状态（不从 API 类型文件 re-export，在此局部定义） ----
export type HealthStatus = "healthy" | "degraded" | "unhealthy";

// ---- 筛选参数 ----
export interface MonitoringFilters {
  dateRange?: [string, string];
  status?: "all" | "running" | "stopped";
  health?: "all" | HealthStatus;
  search?: string;
}

// ---- 聚合 KPI ----
export interface MonitoringKpis {
  totalTenants: number;
  runningTenants: number;
  stoppedTenants: number;
  unhealthyTenants: number;
  enabledAgents: number;
  totalTokens: number;
  totalCalls: number;
  totalChats: number;
}

// ---- 租户行（矩阵表格用） ----
export interface TenantRow {
  key: string;
  tenantId: string;
  agentId: string;
  agentName: string;
  running: boolean;
  health: HealthStatus | null;
  model: string | null;
  workspaceDir: string;
  exists: boolean;
  initialized: boolean;
  updatedAt: string | null;
  chatCount: number;
  jobCount: number;
  tokens: number;
  calls: number;
}

// ---- 关注项 ----
export type AttentionSeverity = "error" | "warning" | "info";

export interface AttentionItem {
  key: string;
  agentId: string;
  tenantId: string;
  agentName: string;
  severity: AttentionSeverity;
  reason: string;
  updatedAt: string | null;
}

// ---- Token 分析行 ----
export interface TokenModelRow {
  key: string;
  providerId: string;
  model: string;
  promptTokens: number;
  completionTokens: number;
  callCount: number;
}

export interface TokenDateRow {
  key: string;
  date: string;
  promptTokens: number;
  completionTokens: number;
  callCount: number;
}

// ================================================================
// 纯函数
// ================================================================

/** 从租户列表 + 健康列表 + Agent 列表构建矩阵行 */
export function buildTenantRows(
  tenants: WecomTenantSummary[],
  healthMap: Record<string, WecomTenantHealthResponse>,
  agents: AgentSummary[],
  tokenMap: Record<string, TokenUsageSummary>,
): TenantRow[] {
  const agentMap = new Map(agents.map((a) => [a.id, a]));
  return tenants.map((t) => {
    const agent = agentMap.get(t.agent_id);
    const health = healthMap[t.agent_id];
    const tokens = tokenMap[t.agent_id];
    return {
      key: t.agent_id,
      tenantId: t.tenant_id,
      agentId: t.agent_id,
      agentName: agent?.name || t.agent_id,
      running: t.running,
      health: health?.status ?? null,
      model: agent?.active_model?.model ?? null,
      workspaceDir: t.workspace_dir,
      exists: t.exists,
      initialized: t.initialized,
      updatedAt: t.updated_at ?? null,
      chatCount: t.chat_count,
      jobCount: t.job_count,
      tokens: tokens
        ? tokens.total_prompt_tokens + tokens.total_completion_tokens
        : 0,
      calls: tokens?.total_calls ?? 0,
    };
  });
}

/** 聚合 KPI */
export function computeKpis(
  rows: TenantRow[],
  agents: AgentSummary[],
): MonitoringKpis {
  return {
    totalTenants: rows.length,
    runningTenants: rows.filter((r) => r.running).length,
    stoppedTenants: rows.filter((r) => !r.running).length,
    unhealthyTenants: rows.filter((r) => r.health === "unhealthy").length,
    enabledAgents: agents.filter((a) => a.enabled).length,
    totalTokens: rows.reduce((s, r) => s + r.tokens, 0),
    totalCalls: rows.reduce((s, r) => s + r.calls, 0),
    totalChats: rows.reduce((s, r) => s + r.chatCount, 0),
  };
}

/** 按筛选条件过滤行 */
export function filterRows(rows: TenantRow[], filters: MonitoringFilters): TenantRow[] {
  let result = rows;

  if (filters.status && filters.status !== "all") {
    const wantRunning = filters.status === "running";
    result = result.filter((r) => r.running === wantRunning);
  }

  if (filters.health && filters.health !== "all") {
    result = result.filter((r) => r.health === filters.health);
  }

  if (filters.search) {
    const q = filters.search.toLowerCase();
    result = result.filter(
      (r) =>
        r.agentId.toLowerCase().includes(q) ||
        r.tenantId.toLowerCase().includes(q) ||
        r.agentName.toLowerCase().includes(q),
    );
  }

  return result;
}

/** 从全局 TokenUsageSummary 提取模型维度表格行 */
export function buildTokenModelRows(summary: TokenUsageSummary | null): TokenModelRow[] {
  if (!summary) return [];
  return Object.entries(summary.by_model).map(([key, stats]) => ({
    key,
    providerId: stats.provider_id ?? "",
    model: stats.model ?? key,
    promptTokens: stats.prompt_tokens,
    completionTokens: stats.completion_tokens,
    callCount: stats.call_count,
  }));
}

/** 从全局 TokenUsageSummary 提取日期维度表格行 */
export function buildTokenDateRows(summary: TokenUsageSummary | null): TokenDateRow[] {
  if (!summary) return [];
  return Object.entries(summary.by_date)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, stats]) => ({
      key: date,
      date,
      promptTokens: stats.prompt_tokens,
      completionTokens: stats.completion_tokens,
      callCount: stats.call_count,
    }));
}

/** 构建关注项列表：异常健康 + workspace 缺失 + agent 停用 */
export function buildAttentionItems(
  rows: TenantRow[],
  agents: AgentSummary[],
): AttentionItem[] {
  const agentMap = new Map(agents.map((a) => [a.id, a]));
  const items: AttentionItem[] = [];

  for (const row of rows) {
    // 健康异常
    if (row.health === "unhealthy") {
      items.push({
        key: `${row.agentId}-unhealthy`,
        agentId: row.agentId,
        tenantId: row.tenantId,
        agentName: row.agentName,
        severity: "error",
        reason: "unhealthy",
        updatedAt: row.updatedAt,
      });
    } else if (row.health === "degraded") {
      items.push({
        key: `${row.agentId}-degraded`,
        agentId: row.agentId,
        tenantId: row.tenantId,
        agentName: row.agentName,
        severity: "warning",
        reason: "degraded",
        updatedAt: row.updatedAt,
      });
    }

    // workspace 缺失
    if (!row.exists) {
      items.push({
        key: `${row.agentId}-no-workspace`,
        agentId: row.agentId,
        tenantId: row.tenantId,
        agentName: row.agentName,
        severity: "warning",
        reason: "workspaceMissing",
        updatedAt: row.updatedAt,
      });
    }

    // Agent 未找到或停用
    const agent = agentMap.get(row.agentId);
    if (!agent) {
      items.push({
        key: `${row.agentId}-no-agent`,
        agentId: row.agentId,
        tenantId: row.tenantId,
        agentName: row.agentName,
        severity: "warning",
        reason: "agentMissing",
        updatedAt: row.updatedAt,
      });
    } else if (!agent.enabled) {
      items.push({
        key: `${row.agentId}-disabled`,
        agentId: row.agentId,
        tenantId: row.tenantId,
        agentName: row.agentName,
        severity: "info",
        reason: "agentDisabled",
        updatedAt: row.updatedAt,
      });
    }
  }

  return items;
}

/** 构建日期范围参数（给 API 用） */
export function buildStatsParams(
  dateRange?: [string, string],
): WecomTenantStatsParams | undefined {
  if (!dateRange) return undefined;
  return { start_date: dateRange[0], end_date: dateRange[1] };
}

/** 兼容子代理 C 的调用签名 */
export function toStatsParams(
  startDate: string,
  endDate: string,
): WecomTenantStatsParams {
  return { start_date: startDate, end_date: endDate };
}

/** 生成管理页跳转路径 */
export function getManagementPath(agentId: string): string {
  return `/wecom-tenants?agentId=${encodeURIComponent(agentId)}`;
}

/** 生成监控下钻路径 */
export function getMonitoringDetailPath(agentId: string): string {
  return `/wecom-tenants/monitoring/${encodeURIComponent(agentId)}`;
}
