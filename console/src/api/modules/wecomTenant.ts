import { request } from "../request";
import { getApiUrl } from "../config";
import { buildAuthHeaders } from "../authHeaders";
import type {
  BadCaseCreateRequest,
  BadCaseUpdateRequest,
  CreateWecomTenantRequest,
  WecomAllTenantHealthResponse,
  WecomLlmRoutingConfig,
  WecomMessageResponse,
  WecomModelSlot,
  WecomTenantAgentStats,
  WecomTenantBadCase,
  WecomTenantBadCaseListResponse,
  WecomTenantBatchOperationRequest,
  WecomTenantBatchOperationResponse,
  WecomTenantBusinessTrace,
  WecomTenantChatListParams,
  WecomTenantChatListResponse,
  WecomTenantCronJob,
  WecomTenantCronJobInput,
  WecomTenantDashboardResponse,
  WecomTenantFileContent,
  WecomTenantFileListResponse,
  WecomTenantGlobalChatListParams,
  WecomTenantHealthResponse,
  WecomTenantListResponse,
  WecomTenantMcpClient,
  WecomTenantMcpCreateRequest,
  WecomTenantOpsOverview,
  WecomTenantOpsSummary,
  WecomTenantSecuritySettings,
  WecomTenantSkill,
  WecomTenantSkillInstallRequest,
  WecomTenantSkillOperationResponse,
  WecomTenantSummary,
  WecomTenantSystemPrompts,
  WecomTenantTokenUsage,
  WecomTenantTool,
  WecomTenantStatsParams,
  WecomToolAsyncExecutionRequest,
} from "../types/wecomTenant";

const rootPath = "/config/channels/wecom_tenant";
const basePath = `${rootPath}/tenants`;

function encoded(value: string): string {
  return encodeURIComponent(value);
}

function withQuery(path: string, params?: object): string {
  if (!params) return path;
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

async function requestBlob(path: string, options: RequestInit = {}) {
  const response = await fetch(getApiUrl(path), {
    ...options,
    headers: {
      ...buildAuthHeaders(),
      ...(options.headers as Record<string, string> | undefined),
    },
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text || `Request failed: ${response.status}`);
  }
  const disposition = response.headers.get("content-disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  return {
    blob: await response.blob(),
    filename: filenameMatch?.[1] || "wecom-tenant.zip",
  };
}

async function requestFormJson<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(getApiUrl(path), {
    method: "POST",
    headers: buildAuthHeaders(),
    body,
  });
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text().catch(() => "");

  if (!response.ok) {
    if (contentType.includes("application/json")) {
      let detail: unknown;
      try {
        const payload = JSON.parse(text) as { detail?: unknown; message?: unknown };
        detail = payload.detail || payload.message;
      } catch {
        detail = null;
      }
      if (typeof detail === "string" && detail) {
        throw new Error(detail);
      }
    }
    throw new Error(text || `Request failed: ${response.status}`);
  }

  if (!contentType.includes("application/json")) {
    return text as unknown as T;
  }
  return JSON.parse(text) as T;
}

export const wecomTenantApi = {
  listWecomTenants: () => request<WecomTenantListResponse>(basePath),

  createWecomTenant: (body: CreateWecomTenantRequest) =>
    request<WecomTenantSummary>(basePath, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  startWecomTenant: (agentId: string) =>
    request<WecomTenantSummary>(
      `${basePath}/${encodeURIComponent(agentId)}/start`,
      { method: "POST" },
    ),

  stopWecomTenant: (agentId: string) =>
    request<WecomTenantSummary>(
      `${basePath}/${encodeURIComponent(agentId)}/stop`,
      { method: "POST" },
    ),

  restartWecomTenant: (agentId: string) =>
    request<WecomTenantSummary>(
      `${basePath}/${encoded(agentId)}/restart`,
      { method: "POST" },
    ),

  getWecomTenantDashboard: () =>
    request<WecomTenantDashboardResponse>(`${rootPath}/stats/dashboard`),

  listWecomTenantHealth: () =>
    request<WecomAllTenantHealthResponse>(`${rootPath}/health`),

  getWecomTenantHealth: (agentId: string) =>
    request<WecomTenantHealthResponse>(
      `${basePath}/${encoded(agentId)}/health`,
    ),

  getWecomTenantModel: (agentId: string) =>
    request<WecomModelSlot | null>(`${basePath}/${encoded(agentId)}/model`),

  updateWecomTenantModel: (agentId: string, body: WecomModelSlot) =>
    request<WecomModelSlot>(`${basePath}/${encoded(agentId)}/model`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  getWecomTenantLlmRouting: (agentId: string) =>
    request<WecomLlmRoutingConfig>(
      `${basePath}/${encoded(agentId)}/llm-routing`,
    ),

  updateWecomTenantLlmRouting: (
    agentId: string,
    body: WecomLlmRoutingConfig,
  ) =>
    request<WecomLlmRoutingConfig>(
      `${basePath}/${encoded(agentId)}/llm-routing`,
      {
        method: "PUT",
        body: JSON.stringify(body),
      },
    ),

  listWecomTenantTools: (agentId: string) =>
    request<WecomTenantTool[]>(`${basePath}/${encoded(agentId)}/tools`),

  toggleWecomTenantTool: (agentId: string, toolName: string) =>
    request<WecomTenantTool>(
      `${basePath}/${encoded(agentId)}/tools/${encoded(toolName)}/toggle`,
      { method: "PATCH" },
    ),

  updateWecomTenantToolAsyncExecution: (
    agentId: string,
    toolName: string,
    body: WecomToolAsyncExecutionRequest,
  ) =>
    request<WecomTenantTool>(
      `${basePath}/${encoded(agentId)}/tools/${encoded(
        toolName,
      )}/async-execution`,
      {
        method: "PATCH",
        body: JSON.stringify(body),
      },
    ),

  listWecomTenantSkills: (agentId: string) =>
    request<WecomTenantSkill[]>(`${basePath}/${encoded(agentId)}/skills`),

  toggleWecomTenantSkill: (agentId: string, skillId: string) =>
    request<WecomTenantSkillOperationResponse>(
      `${basePath}/${encoded(agentId)}/skills/${encoded(skillId)}/toggle`,
      { method: "PATCH" },
    ),

  installWecomTenantSkill: (
    agentId: string,
    body: WecomTenantSkillInstallRequest,
  ) =>
    request<WecomTenantSkillOperationResponse>(
      `${basePath}/${encoded(agentId)}/skills/install`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),

  deleteWecomTenantSkill: (agentId: string, skillId: string) =>
    request<WecomTenantSkillOperationResponse>(
      `${basePath}/${encoded(agentId)}/skills/${encoded(skillId)}`,
      { method: "DELETE" },
    ),

  listWecomTenantMcp: (agentId: string) =>
    request<WecomTenantMcpClient[]>(`${basePath}/${encoded(agentId)}/mcp`),

  createWecomTenantMcp: (
    agentId: string,
    body: WecomTenantMcpCreateRequest,
  ) =>
    request<WecomTenantMcpClient>(`${basePath}/${encoded(agentId)}/mcp`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateWecomTenantMcp: (
    agentId: string,
    clientKey: string,
    body: Omit<WecomTenantMcpClient, "client_key">,
  ) =>
    request<WecomTenantMcpClient>(
      `${basePath}/${encoded(agentId)}/mcp/${encoded(clientKey)}`,
      {
        method: "PUT",
        body: JSON.stringify(body),
      },
    ),

  toggleWecomTenantMcp: (agentId: string, clientKey: string) =>
    request<WecomTenantMcpClient>(
      `${basePath}/${encoded(agentId)}/mcp/${encoded(clientKey)}/toggle`,
      { method: "PATCH" },
    ),

  deleteWecomTenantMcp: (agentId: string, clientKey: string) =>
    request<WecomMessageResponse>(
      `${basePath}/${encoded(agentId)}/mcp/${encoded(clientKey)}`,
      { method: "DELETE" },
    ),

  getWecomTenantSecurity: (agentId: string) =>
    request<WecomTenantSecuritySettings>(
      `${basePath}/${encoded(agentId)}/security`,
    ),

  updateWecomTenantSecurity: (
    agentId: string,
    body: WecomTenantSecuritySettings,
  ) =>
    request<WecomTenantSecuritySettings>(
      `${basePath}/${encoded(agentId)}/security`,
      {
        method: "PUT",
        body: JSON.stringify(body),
      },
    ),

  getWecomTenantSystemPrompts: (agentId: string) =>
    request<WecomTenantSystemPrompts>(
      `${basePath}/${encoded(agentId)}/system-prompts`,
    ),

  updateWecomTenantSystemPrompts: (
    agentId: string,
    body: WecomTenantSystemPrompts,
  ) =>
    request<WecomTenantSystemPrompts>(
      `${basePath}/${encoded(agentId)}/system-prompts`,
      {
        method: "PUT",
        body: JSON.stringify(body),
      },
    ),

  getWecomTenantTokenUsage: (agentId: string, params?: WecomTenantStatsParams) =>
    request<WecomTenantTokenUsage>(
      withQuery(`${basePath}/${encoded(agentId)}/stats/token-usage`, params),
    ),

  getGlobalWecomTenantTokenUsage: (params?: WecomTenantStatsParams) =>
    request<WecomTenantTokenUsage>(
      withQuery(`${rootPath}/stats/token-usage`, params),
    ),

  getWecomTenantAgentStats: (agentId: string, params?: WecomTenantStatsParams) =>
    request<WecomTenantAgentStats>(
      withQuery(`${basePath}/${encoded(agentId)}/stats/agent`, params),
    ),

  getGlobalWecomTenantAgentStats: (params?: WecomTenantStatsParams) =>
    request<WecomTenantAgentStats>(
      withQuery(`${rootPath}/stats/agent`, params),
    ),

  listWecomTenantChats: (
    agentId: string,
    params?: WecomTenantChatListParams,
  ) =>
    request<WecomTenantChatListResponse>(
      withQuery(`${basePath}/${encoded(agentId)}/stats/chats`, params),
    ),

  getWecomTenantChatSession: (agentId: string, sessionId: string) =>
    request<Record<string, unknown>>(
      `${basePath}/${encoded(agentId)}/stats/chats/${encoded(sessionId)}`,
    ),

  listGlobalWecomTenantChats: (params?: WecomTenantGlobalChatListParams) =>
    request<WecomTenantChatListResponse>(
      withQuery(`${rootPath}/stats/chats`, params),
    ),

  listWecomTenantFiles: (agentId: string) =>
    request<WecomTenantFileListResponse>(
      `${basePath}/${encoded(agentId)}/files`,
    ),

  getWecomTenantFile: (agentId: string, filename: string) =>
    request<WecomTenantFileContent>(
      `${basePath}/${encoded(agentId)}/files/${encoded(filename)}`,
    ),

  updateWecomTenantFile: (
    agentId: string,
    filename: string,
    content: string,
  ) =>
    request<WecomTenantFileContent>(
      `${basePath}/${encoded(agentId)}/files/${encoded(filename)}`,
      {
        method: "PUT",
        body: JSON.stringify({ content }),
      },
    ),

  listWecomTenantMemory: (agentId: string) =>
    request<WecomTenantFileListResponse>(
      `${basePath}/${encoded(agentId)}/memory`,
    ),

  getWecomTenantMemoryFile: (agentId: string, filename: string) =>
    request<WecomTenantFileContent>(
      `${basePath}/${encoded(agentId)}/memory/${encoded(filename)}`,
    ),

  updateWecomTenantMemoryFile: (
    agentId: string,
    filename: string,
    content: string,
  ) =>
    request<WecomTenantFileContent>(
      `${basePath}/${encoded(agentId)}/memory/${encoded(filename)}`,
      {
        method: "PUT",
        body: JSON.stringify({ content }),
      },
    ),

  deleteWecomTenantMemoryFile: (agentId: string, filename: string) =>
    request<WecomMessageResponse>(
      `${basePath}/${encoded(agentId)}/memory/${encoded(filename)}`,
      { method: "DELETE" },
    ),

  listWecomTenantCronJobs: (agentId: string) =>
    request<WecomTenantCronJob[]>(`${basePath}/${encoded(agentId)}/cron`),

  createWecomTenantCronJob: (agentId: string, body: WecomTenantCronJobInput) =>
    request<WecomTenantCronJob>(`${basePath}/${encoded(agentId)}/cron`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateWecomTenantCronJob: (
    agentId: string,
    jobId: string,
    body: WecomTenantCronJobInput,
  ) =>
    request<WecomTenantCronJob>(
      `${basePath}/${encoded(agentId)}/cron/${encoded(jobId)}`,
      {
        method: "PUT",
        body: JSON.stringify(body),
      },
    ),

  deleteWecomTenantCronJob: (agentId: string, jobId: string) =>
    request<void>(`${basePath}/${encoded(agentId)}/cron/${encoded(jobId)}`, {
      method: "DELETE",
    }),

  pauseWecomTenantCronJob: (agentId: string, jobId: string) =>
    request<void>(
      `${basePath}/${encoded(agentId)}/cron/${encoded(jobId)}/pause`,
      { method: "POST" },
    ),

  resumeWecomTenantCronJob: (agentId: string, jobId: string) =>
    request<void>(
      `${basePath}/${encoded(agentId)}/cron/${encoded(jobId)}/resume`,
      { method: "POST" },
    ),

  runWecomTenantCronJob: (agentId: string, jobId: string) =>
    request<void>(
      `${basePath}/${encoded(agentId)}/cron/${encoded(jobId)}/run`,
      { method: "POST" },
    ),

  batchStartWecomTenants: (body: WecomTenantBatchOperationRequest) =>
    request<WecomTenantBatchOperationResponse>(`${basePath}/batch/start`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  batchStopWecomTenants: (body: WecomTenantBatchOperationRequest) =>
    request<WecomTenantBatchOperationResponse>(`${basePath}/batch/stop`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  batchRestartWecomTenants: (body: WecomTenantBatchOperationRequest) =>
    request<WecomTenantBatchOperationResponse>(`${basePath}/batch/restart`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  reloadWecomTenant: (agentId: string) =>
    request<WecomMessageResponse>(`${basePath}/${encoded(agentId)}/reload`, {
      method: "POST",
    }),

  deleteWecomTenant: (agentId: string) =>
    request<WecomMessageResponse>(`${basePath}/${encoded(agentId)}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: true }),
    }),

  exportWecomTenant: (agentId: string) =>
    requestBlob(`${basePath}/${encoded(agentId)}/export`),

  importWecomTenant: (agentId: string, file: File, overwrite = false) => {
    const body = new FormData();
    body.append("file", file);
    return requestFormJson<WecomMessageResponse>(
      withQuery(`${basePath}/${encoded(agentId)}/import`, { overwrite }),
      body,
    );
  },

  // ── 运营管理 ──────────────────────────────────────────────────────────────

  getTenantOpsOverview: () =>
    request<WecomTenantOpsOverview>(`${rootPath}/ops/overview`),

  getTenantOpsSummary: (agentId: string) =>
    request<WecomTenantOpsSummary>(
      `${basePath}/${encoded(agentId)}/ops/summary`,
    ),

  listTenantBusinessTraces: (
    agentId: string,
    params?: Record<string, string>,
  ) =>
    request<{ items: WecomTenantBusinessTrace[] }>(
      withQuery(`${basePath}/${encoded(agentId)}/ops/traces`, params),
    ),

  listTenantBadCases: (agentId: string) =>
    request<WecomTenantBadCaseListResponse>(
      `${basePath}/${encoded(agentId)}/bad-cases`,
    ),

  markTenantBadCase: (agentId: string, body: BadCaseCreateRequest) =>
    request<WecomTenantBadCase>(
      `${basePath}/${encoded(agentId)}/bad-cases`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  updateTenantBadCase: (
    agentId: string,
    caseId: string,
    body: BadCaseUpdateRequest,
  ) =>
    request<WecomTenantBadCase>(
      `${basePath}/${encoded(agentId)}/bad-cases/${encoded(caseId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),
};
