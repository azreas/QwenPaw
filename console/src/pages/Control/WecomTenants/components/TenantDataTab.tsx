import { TenantChatsTab } from "./TenantChatsTab";
import { TenantFilesMemoryTab } from "./TenantFilesMemoryTab";
import { TenantMonitoringTab } from "./TenantMonitoringTab";
import styles from "../index.module.less";

interface Props {
  agentId: string;
}

export function TenantDataTab({ agentId }: Props) {
  return (
    <div className={styles.tabStack}>
      <TenantMonitoringTab agentId={agentId} />
      <TenantChatsTab agentId={agentId} />
      <TenantFilesMemoryTab agentId={agentId} />
    </div>
  );
}
