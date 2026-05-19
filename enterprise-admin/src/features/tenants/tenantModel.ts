import type { WecomTenantSummary } from "@/api/types"

/** 租户统计摘要 */
export interface TenantStats {
  total: number
  running: number
  initialized: number
  runtimeOnly: number
  totalChats: number
  totalJobs: number
}

/** 租户展示状态 */
export interface TenantDisplayStatus {
  label: string
  color: "green" | "blue" | "orange" | "default"
}

/** 根据租户列表计算统计摘要 */
export function buildTenantStats(tenants: WecomTenantSummary[]): TenantStats {
  return tenants.reduce<TenantStats>(
    (stats, tenant) => ({
      total: stats.total + 1,
      running: stats.running + (tenant.running ? 1 : 0),
      initialized: stats.initialized + (tenant.initialized ? 1 : 0),
      runtimeOnly: stats.runtimeOnly + (tenant.source === "runtime" ? 1 : 0),
      totalChats: stats.totalChats + tenant.chat_count,
      totalJobs: stats.totalJobs + tenant.job_count,
    }),
    {
      total: 0,
      running: 0,
      initialized: 0,
      runtimeOnly: 0,
      totalChats: 0,
      totalJobs: 0,
    },
  )
}

/** 根据租户状态映射展示标签和颜色 */
export function getTenantDisplayStatus(
  tenant: WecomTenantSummary,
): TenantDisplayStatus {
  if (tenant.running) {
    return { label: "运行中", color: "green" }
  }
  if (tenant.initialized) {
    return { label: "已初始化", color: "blue" }
  }
  if (tenant.exists) {
    return { label: "未初始化", color: "orange" }
  }
  return { label: "仅运行时", color: "default" }
}

/** 按运行状态和更新时间排序租户列表（运行中优先，然后按更新时间倒序） */
export function sortTenantsForTable(
  tenants: WecomTenantSummary[],
): WecomTenantSummary[] {
  return [...tenants].sort((a, b) => {
    if (a.running !== b.running) {
      return a.running ? -1 : 1
    }
    return (b.updated_at || "").localeCompare(a.updated_at || "")
  })
}
