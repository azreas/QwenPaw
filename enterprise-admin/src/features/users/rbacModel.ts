import type { AdminUser } from "@/api/types"

/** 后端默认角色权限定义 */
export const DEFAULT_ROLE_DEFINITIONS = {
  platform_admin: ["*:*"],
  tenant_admin: [
    "tenant:*",
    "agents:*",
    "webchat:*",
    "skills:*",
    "mcp:*",
    "audit:read",
    "auth_users:read",
    "auth_users:write",
    "tasks:*",
  ],
  tenant_member: [
    "webchat:read",
    "webchat:write",
    "skills:call",
    "mcp:call",
    "tasks:read",
  ],
  tenant_readonly: ["webchat:read", "audit:read", "tasks:read"],
} as const

export type DefaultRole = keyof typeof DEFAULT_ROLE_DEFINITIONS

/** 权限矩阵行 */
export interface PermissionMatrixRow {
  permission: string
  platform_admin: boolean
  tenant_admin: boolean
  tenant_member: boolean
  tenant_readonly: boolean
}

/** 用户统计 */
export interface UserStats {
  total: number
  enabled: number
  disabled: number
  platformAdmins: number
  tenantScoped: number
}

/** 角色中文标签映射 */
const ROLE_LABELS: Record<string, string> = {
  platform_admin: "平台管理员",
  tenant_admin: "租户管理员",
  tenant_member: "租户成员",
  tenant_readonly: "租户只读",
}

/** 获取角色显示标签，未知角色返回原始字符串 */
export function getRoleLabel(role: string): string {
  return ROLE_LABELS[role] || role
}

/** 规范化用户角色列表：去重、去空，空数组默认为 tenant_member */
export function normalizeUserRoles(roles: string[]): string[] {
  const cleaned = roles.map((role) => role.trim()).filter(Boolean)
  return cleaned.length > 0 ? Array.from(new Set(cleaned)) : ["tenant_member"]
}

/** 根据用户列表构建统计数据 */
export function buildUserStats(users: AdminUser[]): UserStats {
  return users.reduce<UserStats>(
    (stats, user) => ({
      total: stats.total + 1,
      enabled: stats.enabled + (user.disabled ? 0 : 1),
      disabled: stats.disabled + (user.disabled ? 1 : 0),
      platformAdmins:
        stats.platformAdmins + (user.roles.includes("platform_admin") ? 1 : 0),
      tenantScoped: stats.tenantScoped + (user.tenant_id ? 1 : 0),
    }),
    {
      total: 0,
      enabled: 0,
      disabled: 0,
      platformAdmins: 0,
      tenantScoped: 0,
    },
  )
}

/** 构建权限矩阵：每个权限对应各角色是否拥有 */
export function buildPermissionMatrix(): PermissionMatrixRow[] {
  const permissions = Array.from(
    new Set(Object.values(DEFAULT_ROLE_DEFINITIONS).flat()),
  ).sort()

  const roleHasPermission = (role: DefaultRole, permission: string): boolean => {
    const rolePermissions = DEFAULT_ROLE_DEFINITIONS[role] as readonly string[]
    return rolePermissions.includes("*:*") || rolePermissions.includes(permission)
  }

  return permissions.map((permission) => ({
    permission,
    platform_admin: roleHasPermission("platform_admin", permission),
    tenant_admin: roleHasPermission("tenant_admin", permission),
    tenant_member: roleHasPermission("tenant_member", permission),
    tenant_readonly: roleHasPermission("tenant_readonly", permission),
  }))
}
