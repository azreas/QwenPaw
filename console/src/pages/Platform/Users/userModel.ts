export const ROLE_LABELS: Record<string, string> = {
  platform_admin: "平台管理员",
  tenant_admin: "租户管理员",
  tenant_member: "租户成员",
  tenant_readonly: "只读观察者",
};

export function formatFailureRate(failed: number, total: number): string {
  if (total === 0) return "0%";
  return `${Math.round((failed / total) * 100)}%`;
}

export function classifyTraceOwner(errorReason: string): string {
  if (errorReason.includes("permission_denied")) return "permission_config";
  if (
    ["timeout", "unreachable", "ConnectionError"].some((k) =>
      errorReason.includes(k),
    )
  )
    return "platform_runtime";
  return "platform_runtime";
}
