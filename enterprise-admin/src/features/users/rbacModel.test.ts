import { describe, expect, it } from "vitest"
import {
  DEFAULT_ROLE_DEFINITIONS,
  buildPermissionMatrix,
  buildUserStats,
  getRoleLabel,
  normalizeUserRoles,
} from "./rbacModel"
import type { AdminUser } from "@/api/types"

const users: AdminUser[] = [
  {
    username: "admin",
    roles: ["platform_admin"],
    tenant_id: "",
    disabled: false,
  },
  {
    username: "alice",
    roles: ["tenant_admin"],
    tenant_id: "acme",
    disabled: true,
  },
]

describe("rbacModel", () => {
  it("keeps role definitions aligned with backend defaults", () => {
    expect(DEFAULT_ROLE_DEFINITIONS.platform_admin).toEqual(["*:*"])
    expect(DEFAULT_ROLE_DEFINITIONS.tenant_admin).toContain("auth_users:write")
    expect(DEFAULT_ROLE_DEFINITIONS.tenant_member).toContain("skills:call")
    expect(DEFAULT_ROLE_DEFINITIONS.tenant_readonly).toContain("audit:read")
  })

  it("builds user stats", () => {
    expect(buildUserStats(users)).toEqual({
      total: 2,
      enabled: 1,
      disabled: 1,
      platformAdmins: 1,
      tenantScoped: 1,
    })
  })

  it("builds permission matrix", () => {
    const matrix = buildPermissionMatrix()
    expect(matrix.find((row) => row.permission === "*:*")?.platform_admin).toBe(true)
    expect(matrix.find((row) => row.permission === "auth_users:write")?.platform_admin).toBe(true)
    expect(matrix.find((row) => row.permission === "auth_users:write")?.tenant_admin).toBe(true)
    expect(matrix.find((row) => row.permission === "auth_users:write")?.tenant_member).toBe(false)
  })

  it("normalizes empty roles and labels roles", () => {
    expect(normalizeUserRoles([])).toEqual(["tenant_member"])
    expect(getRoleLabel("tenant_admin")).toBe("租户管理员")
    expect(getRoleLabel("custom_role")).toBe("custom_role")
  })

  it("falls back to tenant_member for falsy or whitespace-only input", () => {
    expect(normalizeUserRoles([""])).toEqual(["tenant_member"])
    expect(normalizeUserRoles(["  "])).toEqual(["tenant_member"])
  })
})
