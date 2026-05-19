import type { MCPClientInfo, SkillInfo, ToolInfo } from "@/api/types"

export interface AbilityStats {
  totalSkills: number
  enabledSkills: number
  installableSkills: number
  totalMcpClients: number
  enabledMcpClients: number
  totalTools: number
  enabledTools: number
  failedCalls: number
}

export interface StatusTag {
  text: string
  color: "green" | "blue" | "orange" | "red" | "default"
}

export function buildAbilityStats(
  skills: SkillInfo[],
  mcpClients: MCPClientInfo[],
  tools: ToolInfo[] = [],
): AbilityStats {
  const failedSkillCalls = skills.filter(
    (item) => item.last_call_status === "failure",
  ).length
  const failedMcpCalls = mcpClients.filter(
    (item) => item.last_call_status === "failure",
  ).length

  return {
    totalSkills: skills.length,
    enabledSkills: skills.filter((item) => item.enabled).length,
    installableSkills: skills.filter((item) => item.installable).length,
    totalMcpClients: mcpClients.length,
    enabledMcpClients: mcpClients.filter((item) => item.enabled).length,
    totalTools: tools.length,
    enabledTools: tools.filter((item) => item.enabled).length,
    failedCalls: failedSkillCalls + failedMcpCalls,
  }
}

export function getAbilityStatusTag(enabled: boolean): StatusTag {
  return enabled
    ? { text: "已启用", color: "green" }
    : { text: "已停用", color: "default" }
}

export function getConnectionTestTag(status?: string | null): StatusTag {
  if (status === "ok") return { text: "连接正常", color: "green" }
  if (status === "timeout") return { text: "连接超时", color: "orange" }
  if (status === "auth_failed") return { text: "认证失败", color: "red" }
  if (status === "unreachable") return { text: "不可达", color: "red" }
  if (status === "invalid_config") return { text: "配置无效", color: "orange" }
  return { text: "未测试", color: "default" }
}

export function formatDurationMs(value?: number | null): string {
  if (value === undefined || value === null) return "-"
  if (value < 1000) return `${Math.round(value)}ms`
  return `${(value / 1000).toFixed(2)}s`
}

export function getLastCallText(
  item: Pick<
    SkillInfo | MCPClientInfo,
    "last_call_status" | "last_error_reason" | "last_duration_ms"
  >,
): string {
  if (!item.last_call_status) {
    return "-"
  }
  if (item.last_error_reason) {
    return `${item.last_call_status} / ${item.last_error_reason}`
  }
  return `${item.last_call_status} / ${formatDurationMs(item.last_duration_ms)}`
}
