import { TenantFeatureConfigTab } from "./TenantFeatureConfigTab";
import { TenantSkillsTab } from "./TenantSkillsTab";
import styles from "../index.module.less";

interface Props {
  agentId: string;
}

export function TenantConfigTab({ agentId }: Props) {
  return (
    <div className={styles.tabStack}>
      <TenantSkillsTab agentId={agentId} />
      <TenantFeatureConfigTab agentId={agentId} />
    </div>
  );
}
