import { get, post } from "./http"
import type {
  CreateWecomTenantRequest,
  WecomTenantListResponse,
  WecomTenantSummary,
} from "./types"

/** 租户 API 基础路径 */
const TENANT_BASE = "/config/channels/wecom_tenant/tenants"

/** 拼接租户操作 URL */
function tenantActionUrl(
  agentId: string,
  action: "start" | "stop" | "restart",
): string {
  return `${TENANT_BASE}/${encodeURIComponent(agentId)}/${action}`
}

/** 获取企微租户列表 */
export function listWecomTenants(): Promise<WecomTenantListResponse> {
  return get<WecomTenantListResponse>(TENANT_BASE)
}

/** 创建企微租户 */
export function createWecomTenant(
  payload: CreateWecomTenantRequest,
): Promise<WecomTenantSummary> {
  return post<WecomTenantSummary>(TENANT_BASE, payload)
}

/** 启动租户 */
export function startWecomTenant(agentId: string): Promise<WecomTenantSummary> {
  return post<WecomTenantSummary>(tenantActionUrl(agentId, "start"))
}

/** 停止租户 */
export function stopWecomTenant(agentId: string): Promise<WecomTenantSummary> {
  return post<WecomTenantSummary>(tenantActionUrl(agentId, "stop"))
}

/** 重启租户 */
export function restartWecomTenant(
  agentId: string,
): Promise<WecomTenantSummary> {
  return post<WecomTenantSummary>(tenantActionUrl(agentId, "restart"))
}
