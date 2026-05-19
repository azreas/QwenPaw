import { describe, expect, it } from "vitest"
import {
  buildTenantStats,
  getTenantDisplayStatus,
  sortTenantsForTable,
} from "./tenantModel"
import type { WecomTenantSummary } from "@/api/types"

const tenants: WecomTenantSummary[] = [
  {
    tenant_id: "beta",
    agent_id: "wx_beta",
    workspace_dir: "D:/tenants/wx_beta",
    exists: true,
    initialized: true,
    running: false,
    updated_at: "2026-05-13T07:00:00+00:00",
    chat_count: 0,
    job_count: 1,
    source: "workspace",
  },
  {
    tenant_id: "acme",
    agent_id: "wx_acme",
    workspace_dir: "D:/tenants/wx_acme",
    exists: true,
    initialized: true,
    running: true,
    updated_at: "2026-05-13T08:00:00+00:00",
    chat_count: 4,
    job_count: 2,
    source: "workspace",
  },
]

describe("tenantModel", () => {
  it("构建租户统计", () => {
    expect(buildTenantStats(tenants)).toEqual({
      total: 2,
      running: 1,
      initialized: 2,
      runtimeOnly: 0,
      totalChats: 4,
      totalJobs: 3,
    })
  })

  it("映射展示状态", () => {
    expect(getTenantDisplayStatus(tenants[1])).toEqual({
      label: "运行中",
      color: "green",
    })
    expect(getTenantDisplayStatus({ ...tenants[0], initialized: false })).toEqual({
      label: "未初始化",
      color: "orange",
    })
  })

  it("按运行状态和更新时间排序", () => {
    expect(sortTenantsForTable(tenants).map((item) => item.agent_id)).toEqual([
      "wx_acme",
      "wx_beta",
    ])
  })
})
