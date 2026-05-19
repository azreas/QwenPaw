import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { WecomTenantSkill } from "../../../../api/types";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import { TenantSkillsSection } from "./feature/TenantSkillsSection";
import styles from "../index.module.less";

interface Props {
  agentId: string;
}

export function TenantSkillsTab({ agentId }: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [skills, setSkills] = useState<WecomTenantSkill[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setSkills(await wecomTenantApi.listWecomTenantSkills(agentId));
    } catch (error) {
      message.error((error as Error).message || t("wecomTenants.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  return (
    <div className={styles.tabContent}>
      <TenantSkillsSection
        agentId={agentId}
        skills={skills}
        loading={loading}
        onRefresh={load}
      />
    </div>
  );
}
