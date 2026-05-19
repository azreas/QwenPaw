import type { WecomTenantSummary } from "../../../../api/types";
import type { TenantRuntimeAction } from "../hooks/useWecomTenants";
import { TenantSummaryTab } from "./TenantSummaryTab";
import { TenantCronTab } from "./TenantCronTab";
import styles from "../index.module.less";

interface Props {
  tenant: WecomTenantSummary;
  onAction: (agentId: string, action: TenantRuntimeAction) => Promise<void>;
}

export function TenantRuntimeTab({ tenant }: Props) {
  return (
    <div className={styles.tabStack}>
      <TenantSummaryTab tenant={tenant} />
      <TenantCronTab agentId={tenant.agent_id} running={tenant.running} />
    </div>
  );
}
