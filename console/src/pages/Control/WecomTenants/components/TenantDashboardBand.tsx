import { useTranslation } from "react-i18next";
import type { WecomTenantDashboardResponse } from "../../../../api/types";
import { formatCompact } from "../../../../utils/formatNumber";
import styles from "../index.module.less";

interface Props {
  dashboard: WecomTenantDashboardResponse | null;
  healthSummary: {
    healthy: number;
    degraded: number;
    unhealthy: number;
  };
  onFilterStatus: (status: string) => void;
}

export function TenantDashboardBand({
  dashboard,
  healthSummary,
  onFilterStatus,
}: Props) {
  const { t } = useTranslation();
  const trendData = (dashboard?.daily_trend || []).map((item) => item.tokens);
  const maxTrend = Math.max(...trendData, 1);

  const metrics = [
    {
      key: "all",
      label: t("wecomTenants.totalTenants"),
      value: dashboard?.total_tenants ?? 0,
      onClick: () => onFilterStatus("all"),
    },
    {
      key: "running",
      label: t("wecomTenants.running"),
      value: dashboard?.running_tenants ?? 0,
      onClick: () => onFilterStatus("running"),
    },
    {
      key: "stopped",
      label: t("wecomTenants.stopped"),
      value: dashboard?.stopped_tenants ?? 0,
      onClick: () => onFilterStatus("stopped"),
    },
    {
      key: "unhealthy",
      label: t("wecomTenants.unhealthy"),
      value: dashboard?.broken_tenants || healthSummary.unhealthy,
      onClick: () => onFilterStatus("unhealthy"),
    },
    {
      key: "tokens",
      label: t("wecomTenants.totalTokens"),
      value: formatCompact(dashboard?.total_tokens ?? 0),
    },
    {
      key: "chats",
      label: t("wecomTenants.totalChats"),
      value: formatCompact(dashboard?.total_chats ?? 0),
    },
    {
      key: "messages",
      label: t("wecomTenants.totalMessages"),
      value: formatCompact(dashboard?.total_messages ?? 0),
    },
  ];
  const healthItems = [
    {
      key: "healthy",
      label: t("wecomTenants.healthy"),
      value: healthSummary.healthy,
    },
    {
      key: "degraded",
      label: t("wecomTenants.degraded"),
      value: healthSummary.degraded,
    },
    {
      key: "unhealthy",
      label: t("wecomTenants.unhealthy"),
      value: healthSummary.unhealthy,
    },
  ];

  return (
    <section className={styles.dashboardBand}>
      <div className={styles.dashboardHeader}>
        <div className={styles.dashboardTitle}>
          <span>{t("wecomTenants.opsOverview")}</span>
          <strong>{t("wecomTenants.tenantControlPlane")}</strong>
        </div>
        <div className={styles.healthStrip}>
          {healthItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`${styles.healthPill} ${styles[`health_${item.key}`]}`}
              onClick={() => onFilterStatus(item.key)}
            >
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </button>
          ))}
        </div>
      </div>
      <div className={styles.dashboardBody}>
        <div className={styles.metricGrid}>
          {metrics.map((item) => (
            <button
              key={item.key}
              type="button"
              className={styles.metricCell}
              onClick={item.onClick}
              disabled={!item.onClick}
            >
              <strong>{item.value}</strong>
              <span>{item.label}</span>
            </button>
          ))}
        </div>
        <div className={styles.trendCell}>
          <span>{t("wecomTenants.tokenTrend")}</span>
          {trendData.length > 1 ? (
            <div className={styles.miniTrend}>
              {trendData.map((value, index) => (
                <i
                  key={`${value}-${index}`}
                  style={{ height: `${Math.max((value / maxTrend) * 100, 8)}%` }}
                />
              ))}
            </div>
          ) : (
            <div className={styles.noTrend}>{t("wecomTenants.noTrend")}</div>
          )}
        </div>
      </div>
    </section>
  );
}
