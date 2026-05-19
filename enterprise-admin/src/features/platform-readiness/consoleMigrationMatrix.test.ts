import { describe, expect, it } from "vitest"
import {
  CONSOLE_MANAGEMENT_ROUTES,
  consoleMigrationMatrix,
  getConsoleMigrationByRoute,
} from "./consoleMigrationMatrix"

describe("consoleMigrationMatrix", () => {
  it("covers every known Console management route", () => {
    const coveredRoutes = consoleMigrationMatrix.map((item) => item.consoleRoute)

    expect(coveredRoutes).toEqual(CONSOLE_MANAGEMENT_ROUTES)
    expect(coveredRoutes).toHaveLength(29)
  })

  it("never treats Console as the product fallback", () => {
    for (const item of consoleMigrationMatrix) {
      expect(item.exitCriteria).not.toMatch(/回到 Console|使用 Console|Console 兜底/)
      expect(item.targetModule).not.toMatch(/Console/)
    }
  })

  it("resolves a known route to enterprise semantics", () => {
    expect(getConsoleMigrationByRoute("/wecom-tenants")).toMatchObject({
      enterpriseMeaning: "企微租户生命周期和配置",
      targetModule: "租户管理 / 业务能力 / Bad Case / 验收测评",
      migrationDecision: "replace-and-rebuild",
    })
  })

  it("returns undefined for routes outside the migration inventory", () => {
    expect(getConsoleMigrationByRoute("/not-a-console-route")).toBeUndefined()
  })
})
