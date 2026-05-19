import { useEffect, useState } from "react";
import { Alert, Spinner } from "@agentscope-ai/design";
import { Card, Table } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type {
  WecomTenantAgentStats,
  WecomTenantChatListResponse,
  WecomTenantHealthResponse,
  WecomTenantSummary,
  WecomTenantTokenUsage,
} from "../../../../api/types";
import { formatCompact } from "../../../../utils/formatNumber";
import styles from "../index.module.less";

interface Props {
  tenant: WecomTenantSummary;
}

interface CheckRow {
  key: string;
  name: string;
  value: unknown;
}

export function TenantSummaryTab({ tenant }: Props) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<WecomTenantHealthResponse | null>(null);
  const [tokens, setTokens] = useState<WecomTenantTokenUsage | null>(null);
  const [stats, setStats] = useState<WecomTenantAgentStats | null>(null);
  const [chats, setChats] = useState<WecomTenantChatListResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    Promise.all([
      wecomTenantApi.getWecomTenantHealth(tenant.agent_id),
      wecomTenantApi.getWecomTenantTokenUsage(tenant.agent_id),
      wecomTenantApi.getWecomTenantAgentStats(tenant.agent_id),
      wecomTenantApi.listWecomTenantChats(tenant.agent_id, {
        page: 1,
        page_size: 5,
      }),
    ])
      .then(([nextHealth, nextTokens, nextStats, nextChats]) => {
        if (!mounted) return;
        setHealth(nextHealth);
        setTokens(nextTokens);
        setStats(nextStats);
        setChats(nextChats);
      })
      .catch((err) => {
        console.error("Failed to load tenant summary:", err);
        if (mounted) setError((err as Error).message);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [tenant.agent_id]);

  const checks = Object.entries(health?.checks || {}).map(([key, value]) => ({
    key,
    name: t(`wecomTenantMonitoring.check_${key}`, key),
    value,
  }));

  const checkColumns: ColumnsType<CheckRow> = [
    { title: t("wecomTenants.check"), dataIndex: "name", key: "name" },
    {
      title: t("wecomTenants.value"),
      dataIndex: "value",
      key: "value",
      render: (value) =>
        typeof value === "boolean"
          ? value
            ? t("common.yes")
            : t("common.no")
          : value
            ? String(value)
            : "-",
    },
  ];

  if (loading) {
    return (
      <div className={styles.tabLoading}>
        <Spinner />
      </div>
    );
  }

  return (
    <div className={styles.tabContent}>
      {error && <Alert type="error" showIcon message={error} />}
      <div className={styles.summaryMetrics}>
        <Card className={styles.metricCard}>
          <strong>
            {formatCompact(
              (tokens?.total_prompt_tokens ?? 0) +
                (tokens?.total_completion_tokens ?? 0),
            )}
          </strong>
          <span>{t("wecomTenants.totalTokens")}</span>
        </Card>
        <Card className={styles.metricCard}>
          <strong>{formatCompact(stats?.total_messages ?? 0)}</strong>
          <span>{t("wecomTenants.totalMessages")}</span>
        </Card>
        <Card className={styles.metricCard}>
          <strong>{formatCompact(stats?.total_tool_calls ?? 0)}</strong>
          <span>{t("wecomTenants.toolCalls")}</span>
        </Card>
        <Card className={styles.metricCard}>
          <strong>{formatCompact(chats?.total ?? tenant.chat_count)}</strong>
          <span>{t("wecomTenants.totalChats")}</span>
        </Card>
      </div>

      <Card title={t("wecomTenants.healthChecks")} bodyStyle={{ padding: 0 }}>
        <Table<CheckRow>
          columns={checkColumns}
          dataSource={checks}
          rowKey="key"
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
}
