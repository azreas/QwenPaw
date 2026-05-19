import { Card } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import { formatCompact } from "../../../../utils/formatNumber";
import type { MonitoringKpis } from "../model";

interface Props {
  kpis: MonitoringKpis;
}

export function MonitoringKpis({ kpis }: Props) {
  const { t } = useTranslation();

  const items = [
    { label: t("wecomTenantMonitoring.totalTenants"), value: kpis.totalTenants },
    { label: t("wecomTenantMonitoring.runningTenants"), value: kpis.runningTenants },
    { label: t("wecomTenantMonitoring.stoppedTenants"), value: kpis.stoppedTenants },
    { label: t("wecomTenantMonitoring.unhealthyTenants"), value: kpis.unhealthyTenants },
    { label: t("wecomTenantMonitoring.enabledAgents"), value: kpis.enabledAgents },
    { label: t("wecomTenantMonitoring.totalTokens"), value: kpis.totalTokens },
    { label: t("wecomTenantMonitoring.totalCalls"), value: kpis.totalCalls },
    { label: t("wecomTenantMonitoring.totalChats"), value: kpis.totalChats },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(120px, 1fr))",
        gap: 12,
      }}
    >
      {items.map((item) => (
        <Card
          key={item.label}
          style={{ padding: 0 }}
          bodyStyle={{ padding: "14px !important" }}
        >
          <strong style={{ display: "block", fontSize: 22, lineHeight: "28px", fontWeight: 600 }}>
            {formatCompact(item.value)}
          </strong>
          <span style={{ display: "block", marginTop: 2, color: "rgba(20,20,19,0.45)", fontSize: 12 }}>
            {item.label}
          </span>
        </Card>
      ))}
    </div>
  );
}
