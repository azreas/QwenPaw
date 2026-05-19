import type { WecomTenantSummary } from "../../../api/types";

export function resolveSelectedTenant(
  tenants: WecomTenantSummary[],
  selectedAgentId: string | null,
): WecomTenantSummary | null {
  return (
    tenants.find((tenant) => tenant.agent_id === selectedAgentId) ||
    tenants[0] ||
    null
  );
}

export function shouldShowMobileDetail(
  selectedAgentId: string | null,
  mobileDetailOpen: boolean,
): boolean {
  return Boolean(selectedAgentId && mobileDetailOpen);
}

export function getRequestedAgentId(search: string): string | null {
  const value = new URLSearchParams(search).get("agentId")?.trim();
  return value || null;
}

export function shouldShowMissingRequestedTenant(
  tenants: WecomTenantSummary[],
  requestedAgentId: string | null,
): boolean {
  return Boolean(
    requestedAgentId &&
      tenants.length > 0 &&
      !tenants.some((tenant) => tenant.agent_id === requestedAgentId),
  );
}
