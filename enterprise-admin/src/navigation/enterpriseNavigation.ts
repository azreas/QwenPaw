/**
 * 企业工作台导航配置
 * 定义企业工作台的菜单结构和路由映射
 */

export interface NavItem {
  key: string
  label: string
  path: string
  icon?: string
  children?: NavItem[]
  group?: string
  availability?: "available" | "mvp" | "planned"
  badge?: string
  requiredRoles?: string[]
}

// 导航项配置 - 企业工作台IA结构
export const enterpriseNavItems: NavItem[] = [
  {
    key: "dashboard",
    label: "运营总览",
    path: "/dashboard",
    group: "overview",
    availability: "available",
  },
  {
    key: "tenants",
    label: "租户管理",
    path: "/tenants",
    group: "management",
    availability: "available",
    requiredRoles: ["platform_admin", "tenant_admin", "tenant_readonly"],
  },
  {
    key: "entryConfig",
    label: "入口配置",
    path: "/entry-config",
    group: "management",
    availability: "available",
    requiredRoles: ["platform_admin", "tenant_admin"],
  },
  {
    key: "users",
    label: "用户与权限",
    path: "/users",
    group: "management",
    availability: "available",
    requiredRoles: ["platform_admin", "tenant_admin"],
  },
  {
    key: "abilities",
    label: "业务能力",
    path: "/abilities",
    group: "management",
    availability: "available",
    requiredRoles: ["platform_admin", "tenant_admin"],
  },
  {
    key: "models",
    label: "模型治理",
    path: "/models",
    group: "governance",
    availability: "available",
    requiredRoles: ["platform_admin"],
  },
  {
    key: "policies",
    label: "策略配置",
    path: "/policies",
    group: "management",
    availability: "available",
    requiredRoles: ["platform_admin"],
  },
  {
    key: "audit",
    label: "业务追踪",
    path: "/audit",
    group: "observability",
    availability: "available",
    requiredRoles: ["platform_admin", "tenant_admin", "tenant_readonly"],
  },
  {
    key: "evaluation",
    label: "验收测评",
    path: "/evaluation",
    group: "acceptance",
    availability: "available",
    requiredRoles: ["platform_admin", "tenant_admin", "tenant_readonly"],
  },
  {
    key: "badCases",
    label: "Bad Case",
    path: "/bad-cases",
    group: "observability",
    availability: "available",
    requiredRoles: ["platform_admin", "tenant_admin"],
  },
  {
    key: "metrics",
    label: "指标监控",
    path: "/metrics",
    group: "observability",
    availability: "available",
    requiredRoles: ["platform_admin"],
  },
  {
    key: "quota",
    label: "配额管理",
    path: "/quota",
    group: "observability",
    availability: "available",
    requiredRoles: ["platform_admin"],
  },
  {
    key: "security",
    label: "安全中心",
    path: "/security",
    group: "security",
    availability: "available",
    requiredRoles: ["platform_admin"],
  },
  {
    key: "backups",
    label: "备份恢复",
    path: "/backups",
    group: "reliability",
    availability: "available",
    requiredRoles: ["platform_admin"],
  },
  {
    key: "diagnostics",
    label: "诊断中心",
    path: "/diagnostics",
    group: "reliability",
    availability: "available",
    requiredRoles: ["platform_admin", "tenant_admin"],
  },
  {
    key: "settings",
    label: "系统设置",
    path: "/settings",
    group: "system",
    availability: "mvp",
    requiredRoles: ["platform_admin"],
  },
]

// 路径到导航key的映射
export const pathToKeyMap: Record<string, string> = {
  "/": "dashboard",
  "/dashboard": "dashboard",
  "/tenants": "tenants",
  "/entry-config": "entryConfig",
  "/users": "users",
  "/abilities": "abilities",
  "/models": "models",
  "/policies": "policies",
  "/audit": "audit",
  "/evaluation": "evaluation",
  "/bad-cases": "badCases",
  "/metrics": "metrics",
  "/quota": "quota",
  "/security": "security",
  "/backups": "backups",
  "/diagnostics": "diagnostics",
  "/settings": "settings",
}

// 导航分组配置
export const navGroups: Record<string, string> = {
  overview: "概览",
  management: "管理中心",
  governance: "治理",
  observability: "可观测性",
  acceptance: "验收",
  reliability: "可靠性",
  security: "安全",
  system: "系统",
}

/**
 * 根据路径解析对应的导航key
 * @param pathname 当前路径
 * @returns 导航key
 */
export function resolveNavKey(pathname: string): string {
  // 精确匹配
  if (pathToKeyMap[pathname]) {
    return pathToKeyMap[pathname]
  }

  // 前缀匹配 - 查找最长匹配的路径（排除 "/" 以避免误匹配）
  const matchedKeys = Object.keys(pathToKeyMap)
    .filter((path) => path !== "/" && pathname.startsWith(path))
    .sort((a, b) => b.length - a.length)

  if (matchedKeys.length > 0) {
    return pathToKeyMap[matchedKeys[0]]
  }

  return ""
}

/**
 * 根据key获取路径
 * @param key 导航key
 * @returns 路径
 */
export function getPathByKey(key: string): string | undefined {
  // 从 enterpriseNavItems 中直接获取路径，避免 pathToKeyMap 中 "/" 的影响
  const item = enterpriseNavItems.find((item) => item.key === key)
  return item?.path
}

/**
 * 获取分组下的所有导航项
 * @param group 分组名称
 * @returns 该分组下的导航项数组
 */
export function getNavItemsByGroup(group: string): NavItem[] {
  return enterpriseNavItems.filter((item) => item.group === group)
}

export function canAccessNavItem(
  item: NavItem,
  role?: string,
  authDisabled = false,
): boolean {
  const normalizedRole = role === "admin" ? "platform_admin" : role
  if (authDisabled || normalizedRole === "platform_admin") {
    return true
  }
  if (!item.requiredRoles || item.requiredRoles.length === 0) {
    return true
  }
  return Boolean(normalizedRole && item.requiredRoles.includes(normalizedRole))
}

export function getVisibleNavItems(
  role?: string,
  authDisabled = false,
): NavItem[] {
  return enterpriseNavItems.filter((item) =>
    canAccessNavItem(item, role, authDisabled),
  )
}

/**
 * 获取所有分组名称
 * @returns 分组名称数组
 */
export function getAllGroups(): string[] {
  return Object.keys(navGroups)
}
