import { useEffect, useState } from "react";
import { Card, Spinner, Statistic, Tag } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { WecomTenantOpsSummary } from "../../../../api/types";
import styles from "../index.module.less";

interface Props {
  agentId: string;
}

export function TenantOperationsOverview({ agentId }: Props) {
  const { t } = useTranslation();
  const [data, setData] = useState<WecomTenantOpsSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!agentId) return;
    setLoading(true);
    wecomTenantApi
      .getTenantOpsSummary(agentId)
      .then(setData)
      .finally(() => setLoading(false));
  }, [agentId]);

  if (loading) return <Spinner />;

  const statusColor =
    data?.health_status === "healthy"
      ? "green"
      : data?.health_status === "degraded"
        ? "orange"
        : "red";
  const failureRate =
    data && data.business_calls_24h > 0
      ? `${Math.round((data.failed_calls_24h / data.business_calls_24h) * 100)}%`
      : "0%";

  return (
    <Card title={t("wecomTenants.operationsOverview")} className={styles.opsCard}>
      <div className={styles.opsStats}>
        <Statistic
          title={t("wecomTenants.calls24h")}
          value={data?.business_calls_24h ?? 0}
        />
        <Statistic
          title={t("wecomTenants.failedCalls24h")}
          value={data?.failed_calls_24h ?? 0}
        />
        <Statistic title={t("wecomTenants.failureRate")} value={failureRate} />
        <div className={styles.opsHealth}>
          <span>{t("wecomTenants.healthStatus")}: </span>
          <Tag color={statusColor}>{data?.health_status ?? "unknown"}</Tag>
        </div>
      </div>
    </Card>
  );
}
