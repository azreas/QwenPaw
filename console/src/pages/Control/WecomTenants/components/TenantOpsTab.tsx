import { useCallback, useState } from "react";
import type { WecomTenantSummary } from "../../../../api/types";
import { TenantBadCasePanel } from "./TenantBadCasePanel";
import { TenantOperationsOverview } from "./TenantOperationsOverview";
import { TenantTraceTable } from "./TenantTraceTable";

interface Props {
  tenant: WecomTenantSummary;
  onDeleted: () => Promise<void>;
}

export function TenantOpsTab({ tenant }: Props) {
  const agentId = tenant.agent_id;
  const [badCaseRefreshKey, setBadCaseRefreshKey] = useState(0);
  const handleBadCaseMarked = useCallback(() => {
    setBadCaseRefreshKey((k) => k + 1);
  }, []);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <TenantOperationsOverview agentId={agentId} />
      <TenantTraceTable agentId={agentId} onMarked={handleBadCaseMarked} />
      <TenantBadCasePanel agentId={agentId} refreshKey={badCaseRefreshKey} />
    </div>
  );
}
