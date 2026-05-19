import { describe, expect, it } from "vitest"
import { enterpriseNavItems } from "@/navigation/enterpriseNavigation"
import {
  ENTERPRISE_PAGE_COMPLETENESS,
  getPageCompleteness,
  getPageCompletenessStatusTag,
} from "./pageCompletenessModel"

describe("pageCompletenessModel", () => {
  it("defines completeness for every Enterprise Admin nav item", () => {
    const completenessKeys = Object.keys(ENTERPRISE_PAGE_COMPLETENESS)
    const navKeys = enterpriseNavItems.map((item) => item.key)

    expect(completenessKeys.sort()).toEqual(navKeys.sort())
  })

  it("marks policies as MVP and settings as MVP with readonly boundaries", () => {
    expect(getPageCompleteness("policies")?.status).toBe("mvp")
    expect(getPageCompleteness("settings")?.status).toBe("mvp")
    expect(getPageCompleteness("policies")?.stagedCapabilities).toEqual(
      expect.arrayContaining(["发布审批", "版本回滚", "批量应用"]),
    )
    expect(getPageCompleteness("settings")?.currentWorkflow.join(" ")).toContain("只读")
    expect(getPageCompleteness("settings")?.currentWorkflow.join(" ")).toContain("合规审计")
    expect(getPageCompleteness("settings")?.stagedCapabilities).toEqual(
      expect.arrayContaining(["在线修改", "默认入口切换", "Console 开关修改"]),
    )
  })

  it("marks metrics as read-only with staged observability follow-ups", () => {
    const metrics = getPageCompleteness("metrics")

    expect(metrics?.status).toBe("read-only")
    expect(metrics?.currentWorkflow.join(" ")).toContain("原始指标")
    expect(metrics?.gaps.join(" ")).toContain("趋势")
    expect(metrics?.stagedCapabilities).toEqual(
      expect.arrayContaining(["告警配置", "趋势图", "导出分析", "跨租户下钻"]),
    )
  })

  it("marks operations, security and reliability modules as MVP with staged risky writes", () => {
    expect(getPageCompleteness("quota")?.status).toBe("mvp")
    expect(getPageCompleteness("security")?.status).toBe("mvp")
    expect(getPageCompleteness("backups")?.status).toBe("mvp")
    expect(getPageCompleteness("diagnostics")?.status).toBe("mvp")
    expect(getPageCompleteness("quota")?.stagedCapabilities).toContain("配额调整")
    expect(getPageCompleteness("security")?.stagedCapabilities).toContain(
      "审批处置",
    )
    expect(getPageCompleteness("backups")?.stagedCapabilities).toContain(
      "真实恢复",
    )
    expect(getPageCompleteness("diagnostics")?.stagedCapabilities).toContain(
      "日志摘要",
    )
  })

  it("marks migrated entry and model modules as MVP", () => {
    expect(getPageCompleteness("entryConfig")?.status).toBe("mvp")
    expect(getPageCompleteness("models")?.status).toBe("mvp")
    expect(getPageCompleteness("entryConfig")?.gaps.join(" ")).toContain(
      "环境变量",
    )
    expect(getPageCompleteness("models")?.stagedCapabilities).toContain(
      "平台模型库存",
    )
  })

  it("tracks ownership for migrated entry, model and reliability modules", () => {
    expect(getPageCompleteness("entryConfig")?.consoleExitRelation).toContain(
      "/channels",
    )
    expect(getPageCompleteness("models")?.consoleExitRelation).toContain(
      "/models",
    )
    expect(getPageCompleteness("backups")?.auditEvents.join(" ")).toContain(
      "恢复",
    )
    expect(getPageCompleteness("diagnostics")?.tenantBoundary).toContain(
      "租户",
    )
  })

  it("keeps core pages honest about MVP gaps", () => {
    expect(getPageCompleteness("tenants")?.backendContracts.join(" ")).toContain(
      "tenant-local system prompts/security",
    )
    expect(getPageCompleteness("tenants")?.stagedCapabilities).toContain(
      "租户模板应用",
    )
    expect(getPageCompleteness("dashboard")?.gaps).toContain(
      "租户聚合、业务追踪聚合、Bad Case 聚合、测评聚合仍需补齐",
    )
    expect(getPageCompleteness("abilities")?.consoleExitRelation).toContain(
      "/skills",
    )
    expect(getPageCompleteness("evaluation")?.stagedCapabilities).toContain(
      "自动问答回放",
    )
  })

  it("uses string fields for completeness text while keeping stagedCapabilities as arrays", () => {
    const dashboard = getPageCompleteness("dashboard")

    expect(typeof dashboard?.completeWhen).toBe("string")
    expect(typeof dashboard?.rbacBoundary).toBe("string")
    expect(typeof dashboard?.tenantBoundary).toBe("string")
    expect(Array.isArray(dashboard?.stagedCapabilities)).toBe(true)
  })

  it("returns undefined for invalid or inherited page keys", () => {
    expect(getPageCompleteness("not-a-page")).toBeUndefined()
    expect(getPageCompleteness("__proto__")).toBeUndefined()
    expect(getPageCompleteness("constructor")).toBeUndefined()
  })

  it("keeps each completeness definition key aligned with its record key", () => {
    for (const [key, definition] of Object.entries(ENTERPRISE_PAGE_COMPLETENESS)) {
      expect(definition.key).toBe(key)
    }
  })

  it("maps status tags", () => {
    expect(getPageCompletenessStatusTag("available")).toEqual({
      color: "green",
      text: "已可用",
    })
    expect(getPageCompletenessStatusTag("mvp")).toEqual({
      color: "blue",
      text: "MVP 可用",
    })
    expect(getPageCompletenessStatusTag("read-only")).toEqual({
      color: "purple",
      text: "只读",
    })
    expect(getPageCompletenessStatusTag("staged")).toEqual({
      color: "orange",
      text: "阶段化开放",
    })
  })
})
