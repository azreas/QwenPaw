import { Card } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import type {
  WecomTenantAgentStats,
  WecomTenantTokenUsage,
} from "../../../../api/types/wecomTenant";
import { formatCompact } from "../../../../utils/formatNumber";
import styles from "../detail.module.less";

interface Props {
  tokenUsage: WecomTenantTokenUsage | null;
  agentStats: WecomTenantAgentStats | null;
}

export function TenantUsagePanel({
  tokenUsage,
  agentStats,
}: Props) {
  const { t } = useTranslation();
  const items = [
    [
      t("wecomTenants.promptTokens"),
      tokenUsage?.total_prompt_tokens ?? 0,
    ],
    [
      t("wecomTenants.completionTokens"),
      tokenUsage?.total_completion_tokens ?? 0,
    ],
    [
      t("wecomTenantMonitoring.calls"),
      tokenUsage?.total_calls ?? 0,
    ],
    [
      t("wecomTenantMonitoring.activeSessions"),
      agentStats?.total_active_sessions ?? 0,
    ],
    [
      t("wecomTenantMonitoring.messages"),
      agentStats?.total_messages ?? 0,
    ],
    [
      t("wecomTenantMonitoring.toolCalls"),
      agentStats?.total_tool_calls ?? 0,
    ],
  ];
  return (
    <Card
      title={t("wecomTenantMonitoring.usageDiagnosis")}
    >
      <div className={styles.detailKpiGrid}>
        {items.map(([label, value]) => (
          <div
            key={label}
            className={styles.detailKpi}
          >
            <strong>
              {formatCompact(Number(value))}
            </strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
