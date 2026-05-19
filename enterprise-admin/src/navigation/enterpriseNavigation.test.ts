import { describe, it, expect } from "vitest"
import { ENTERPRISE_PAGE_COMPLETENESS } from "@/features/platform-readiness/pageCompletenessModel"
import {
  enterpriseNavItems,
  pathToKeyMap,
  navGroups,
  resolveNavKey,
  getPathByKey,
  getNavItemsByGroup,
  getAllGroups,
  getVisibleNavItems,
  canAccessNavItem,
} from "./enterpriseNavigation"

describe("enterpriseNavigation", () => {
  it("导航项与页面完整性定义保持一致", () => {
    const navKeys = enterpriseNavItems.map((item) => item.key).sort()
    const completenessKeys = Object.keys(ENTERPRISE_PAGE_COMPLETENESS).sort()

    expect(completenessKeys).toEqual(navKeys)
  })

  describe("enterpriseNavItems", () => {
    it("应该包含所有预期的导航项", () => {
      const keys = enterpriseNavItems.map((item) => item.key)
      expect(keys).toContain("dashboard")
      expect(keys).toContain("tenants")
      expect(keys).toContain("entryConfig")
      expect(keys).toContain("users")
      expect(keys).toContain("abilities")
      expect(keys).toContain("models")
      expect(keys).toContain("policies")
      expect(keys).toContain("audit")
      expect(keys).toContain("badCases")
      expect(keys).toContain("evaluation")
      expect(keys).toContain("metrics")
      expect(keys).toContain("quota")
      expect(keys).toContain("security")
      expect(keys).toContain("backups")
      expect(keys).toContain("diagnostics")
      expect(keys).toContain("settings")
    })

    it("覆盖企业平台完整 IA 要求", () => {
      const labels = enterpriseNavItems.map((item) => item.label)

      expect(labels).toEqual(
        expect.arrayContaining([
          "运营总览",
          "租户管理",
          "入口配置",
          "业务能力",
          "模型治理",
          "用户与权限",
          "策略配置",
          "指标监控",
          "配额管理",
          "安全中心",
          "业务追踪",
          "Bad Case",
          "验收测评",
          "备份恢复",
          "诊断中心",
          "系统设置",
        ]),
      )
    })

    it("每个导航项都应该有有效的路径", () => {
      enterpriseNavItems.forEach((item) => {
        expect(item.path).toBeDefined()
        expect(item.path).toMatch(/^\//)
      })
    })

    it("每个导航项都应该属于有效的分组", () => {
      const groupKeys = Object.keys(navGroups)
      enterpriseNavItems.forEach((item) => {
        expect(item.group).toBeDefined()
        expect(groupKeys).toContain(item.group)
      })
    })

    it("未实现模块应该明确标记为未开放", () => {
      const plannedKeys = ["settings"]

      plannedKeys.forEach((key) => {
        const item = enterpriseNavItems.find((item) => item.key === key)
        expect(item?.availability).toBe("planned")
        expect(item?.badge).toBe("未开放")
      })
    })

    it("已实现的验收测评不应被标记为未开放", () => {
      const availableKeys = [
        "entryConfig",
        "models",
        "metrics",
        "evaluation",
        "quota",
        "security",
        "backups",
        "diagnostics",
      ]

      availableKeys.forEach((key) => {
        const item = enterpriseNavItems.find((item) => item.key === key)
        expect(item?.availability).toBe("available")
        expect(item?.badge).toBeUndefined()
      })
    })

    it("策略配置已作为 MVP 页面开放", () => {
      const item = enterpriseNavItems.find((navItem) => navItem.key === "policies")

      expect(item).toMatchObject({
        key: "policies",
        label: "策略配置",
        path: "/policies",
        availability: "available",
        requiredRoles: ["platform_admin"],
      })
      expect(item?.badge).toBeUndefined()
    })

    it("指标监控已作为只读摘要页开放", () => {
      const item = enterpriseNavItems.find((navItem) => navItem.key === "metrics")

      expect(item).toMatchObject({
        key: "metrics",
        label: "指标监控",
        path: "/metrics",
        availability: "available",
        requiredRoles: ["platform_admin"],
      })
      expect(item?.badge).toBeUndefined()
    })
  })

  describe("pathToKeyMap", () => {
    it("应该正确映射根路径到dashboard", () => {
      expect(pathToKeyMap["/"]).toBe("dashboard")
    })

    it("应该正确映射所有导航路径", () => {
      enterpriseNavItems.forEach((item) => {
        expect(pathToKeyMap[item.path]).toBe(item.key)
      })
    })
  })

  describe("resolveNavKey", () => {
    it("应该正确解析精确匹配的路径", () => {
      expect(resolveNavKey("/dashboard")).toBe("dashboard")
      expect(resolveNavKey("/tenants")).toBe("tenants")
      expect(resolveNavKey("/users")).toBe("users")
      expect(resolveNavKey("/abilities")).toBe("abilities")
      expect(resolveNavKey("/models")).toBe("models")
      expect(resolveNavKey("/evaluation")).toBe("evaluation")
    })

    it("平台级治理模块应该声明平台管理员可见", () => {
      const platformOnlyKeys = [
        "models",
        "policies",
        "metrics",
        "quota",
        "security",
        "backups",
        "settings",
      ]

      platformOnlyKeys.forEach((key) => {
        const item = enterpriseNavItems.find((item) => item.key === key)
        expect(item?.requiredRoles).toEqual(["platform_admin"])
      })
    })

    it("应该正确解析 /users 子路径", () => {
      expect(resolveNavKey("/users/roles")).toBe("users")
    })

    it("应该正确解析 /abilities 子路径", () => {
      expect(resolveNavKey("/abilities/wx_acme")).toBe("abilities")
    })

    it("应该正确解析迁移期治理模块子路径", () => {
      expect(resolveNavKey("/entry-config/wx_acme")).toBe("entryConfig")
      expect(resolveNavKey("/models/routes")).toBe("models")
      expect(resolveNavKey("/backups/restore")).toBe("backups")
      expect(resolveNavKey("/diagnostics/readiness")).toBe("diagnostics")
    })

    it("应该正确解析 /evaluation 子路径", () => {
      expect(resolveNavKey("/evaluation/datasets")).toBe("evaluation")
    })

    it("应该正确解析根路径", () => {
      expect(resolveNavKey("/")).toBe("dashboard")
    })

    it("对于未知路径应该返回空字符串", () => {
      expect(resolveNavKey("/unknown-path")).toBe("")
    })
  })

  describe("getPathByKey", () => {
    it("应该根据key返回正确的路径", () => {
      expect(getPathByKey("dashboard")).toBe("/dashboard")
      expect(getPathByKey("tenants")).toBe("/tenants")
      expect(getPathByKey("users")).toBe("/users")
      expect(getPathByKey("abilities")).toBe("/abilities")
      expect(getPathByKey("entryConfig")).toBe("/entry-config")
      expect(getPathByKey("models")).toBe("/models")
      expect(getPathByKey("evaluation")).toBe("/evaluation")
      expect(getPathByKey("backups")).toBe("/backups")
      expect(getPathByKey("diagnostics")).toBe("/diagnostics")
    })

    it("对于不存在的key应该返回undefined", () => {
      expect(getPathByKey("nonexistent")).toBeUndefined()
    })

    it("users 导航项标签应为'用户与权限'", () => {
      const usersItem = enterpriseNavItems.find((item) => item.key === "users")
      expect(usersItem?.label).toBe("用户与权限")
    })

    it("audit 导航项应指向业务追踪", () => {
      const auditItem = enterpriseNavItems.find((item) => item.key === "audit")
      expect(auditItem?.label).toBe("业务追踪")
      expect(resolveNavKey("/audit")).toBe("audit")
      expect(resolveNavKey("/audit/traces")).toBe("audit")
      expect(getPathByKey("audit")).toBe("/audit")
    })

    it("badCases 导航项应指向 Bad Case 管理", () => {
      const badCasesItem = enterpriseNavItems.find(
        (item) => item.key === "badCases",
      )
      expect(badCasesItem?.label).toBe("Bad Case")
      expect(resolveNavKey("/bad-cases")).toBe("badCases")
      expect(resolveNavKey("/bad-cases/case-audit-1")).toBe("badCases")
      expect(getPathByKey("badCases")).toBe("/bad-cases")
    })
  })

  describe("getNavItemsByGroup", () => {
    it("应该返回指定分组下的所有导航项", () => {
      const overviewItems = getNavItemsByGroup("overview")
      expect(overviewItems).toHaveLength(1)
      expect(overviewItems[0].key).toBe("dashboard")

      const managementItems = getNavItemsByGroup("management")
      expect(managementItems).toHaveLength(5)
      expect(managementItems.map((i) => i.key)).toEqual(
        expect.arrayContaining([
          "tenants",
          "entryConfig",
          "users",
          "abilities",
          "policies",
        ]),
      )

      const governanceItems = getNavItemsByGroup("governance")
      expect(governanceItems.map((i) => i.key)).toEqual(["models"])

      const observabilityItems = getNavItemsByGroup("observability")
      expect(observabilityItems.map((i) => i.key)).toEqual(
        expect.arrayContaining(["audit", "badCases", "metrics", "quota"]),
      )

      const acceptanceItems = getNavItemsByGroup("acceptance")
      expect(acceptanceItems.map((item) => item.key)).toEqual(["evaluation"])

      const reliabilityItems = getNavItemsByGroup("reliability")
      expect(reliabilityItems.map((i) => i.key)).toEqual(
        expect.arrayContaining(["backups", "diagnostics"]),
      )
    })

    it("对于不存在的分组应该返回空数组", () => {
      expect(getNavItemsByGroup("nonexistent")).toEqual([])
    })
  })

  describe("role-aware navigation", () => {
    it("platform_admin can access every Enterprise Admin module", () => {
      const visibleKeys = getVisibleNavItems("platform_admin").map(
        (item) => item.key,
      )
      expect(visibleKeys).toEqual(enterpriseNavItems.map((item) => item.key))
    })

    it("legacy admin role keeps platform administrator navigation visible", () => {
      const visibleKeys = getVisibleNavItems("admin").map((item) => item.key)

      expect(visibleKeys).toEqual(enterpriseNavItems.map((item) => item.key))
    })

    it("tenant_admin sees tenant-scoped modules but not platform-only modules", () => {
      const visibleKeys = getVisibleNavItems("tenant_admin").map(
        (item) => item.key,
      )

      expect(visibleKeys).toEqual(
        expect.arrayContaining([
          "dashboard",
          "tenants",
          "entryConfig",
          "users",
          "abilities",
          "audit",
          "evaluation",
          "badCases",
          "diagnostics",
        ]),
      )
      expect(visibleKeys).not.toContain("models")
      expect(visibleKeys).not.toContain("policies")
      expect(visibleKeys).not.toContain("security")
      expect(visibleKeys).not.toContain("backups")
      expect(visibleKeys).not.toContain("settings")
    })

    it("tenant_readonly only sees read and review modules", () => {
      const visibleKeys = getVisibleNavItems("tenant_readonly").map(
        (item) => item.key,
      )

      expect(visibleKeys).toEqual(
        expect.arrayContaining(["dashboard", "tenants", "audit", "evaluation"]),
      )
      expect(visibleKeys).not.toContain("users")
      expect(visibleKeys).not.toContain("abilities")
    })

    it("auth-disabled local mode keeps every module visible", () => {
      expect(
        canAccessNavItem(
          enterpriseNavItems.find((item) => item.key === "security")!,
          undefined,
          true,
        ),
      ).toBe(true)
    })
  })

  describe("getAllGroups", () => {
    it("应该返回所有分组名称", () => {
      const groups = getAllGroups()
      expect(groups).toContain("overview")
      expect(groups).toContain("management")
      expect(groups).toContain("observability")
      expect(groups).toContain("acceptance")
      expect(groups).toContain("security")
      expect(groups).toContain("system")
    })

    it("返回的分组数量应该与navGroups中的键数量一致", () => {
      const groups = getAllGroups()
      expect(groups.length).toBe(Object.keys(navGroups).length)
    })
  })

  describe("navGroups", () => {
    it("应该包含所有预期的分组标签", () => {
      expect(navGroups.overview).toBe("概览")
      expect(navGroups.management).toBe("管理中心")
      expect(navGroups.governance).toBe("治理")
      expect(navGroups.observability).toBe("可观测性")
      expect(navGroups.acceptance).toBe("验收")
      expect(navGroups.reliability).toBe("可靠性")
      expect(navGroups.security).toBe("安全")
      expect(navGroups.system).toBe("系统")
    })
  })
})
