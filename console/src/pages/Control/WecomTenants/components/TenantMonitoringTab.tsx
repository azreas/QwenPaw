import { useEffect, useMemo, useState } from "react";
import { DatePicker, Empty, Spinner } from "@agentscope-ai/design";
import { Column } from "@ant-design/plots";
import { Button, Card, Select, Table } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import dayjs, { Dayjs } from "dayjs";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type {
  ChannelStats,
  TokenUsageStats,
  WecomTenantAgentStats,
  WecomTenantTokenUsage,
} from "../../../../api/types";
import { formatCompact } from "../../../../utils/formatNumber";
import styles from "../index.module.less";

interface Props {
  agentId: string;
}

type ModelRow = TokenUsageStats & { key: string };

export function TenantMonitoringTab({ agentId }: Props) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState<Dayjs>(dayjs().subtract(30, "day"));
  const [endDate, setEndDate] = useState<Dayjs>(dayjs());
  const [provider, setProvider] = useState<string | undefined>();
  const [modelName, setModelName] = useState<string | undefined>();
  const [tokens, setTokens] = useState<WecomTenantTokenUsage | null>(null);
  const [stats, setStats] = useState<WecomTenantAgentStats | null>(null);

  const load = async (
    start = startDate,
    end = endDate,
    providerId = provider,
    model = modelName,
  ) => {
    setLoading(true);
    try {
      const params = {
        start_date: start.format("YYYY-MM-DD"),
        end_date: end.format("YYYY-MM-DD"),
        provider: providerId,
        model,
      };
      const [tokenData, statData] = await Promise.all([
        wecomTenantApi.getWecomTenantTokenUsage(agentId, params),
        wecomTenantApi.getWecomTenantAgentStats(agentId, params),
      ]);
      setTokens(tokenData);
      setStats(statData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  const modelRows = useMemo<ModelRow[]>(
    () =>
      Object.entries(tokens?.by_model || {}).map(([key, value]) => ({
        ...value,
        key,
      })),
    [tokens?.by_model],
  );

  const providerOptions = useMemo(
    () =>
      Array.from(
        new Set(modelRows.map((row) => row.provider_id).filter(Boolean)),
      ) as string[],
    [modelRows],
  );

  const modelOptions = useMemo(
    () =>
      Array.from(
        new Set(
          modelRows
            .filter((row) => !provider || row.provider_id === provider)
            .map((row) => row.model)
            .filter(Boolean),
        ),
      ) as string[],
    [modelRows, provider],
  );

  const chartData = useMemo(
    () =>
      (stats?.by_date || []).flatMap((item) => [
        {
          date: dayjs(item.date).format("MM-DD"),
          type: t("wecomTenants.totalMessages"),
          value: item.total_messages,
        },
        {
          date: dayjs(item.date).format("MM-DD"),
          type: t("wecomTenants.toolCalls"),
          value: item.tool_calls,
        },
        {
          date: dayjs(item.date).format("MM-DD"),
          type: t("wecomTenants.llmCalls"),
          value: item.llm_calls,
        },
        {
          date: dayjs(item.date).format("MM-DD"),
          type: t("wecomTenants.activeSessions"),
          value: item.active_sessions,
        },
      ]),
    [stats?.by_date, t],
  );

  const channelColumns: ColumnsType<ChannelStats> = [
    { title: t("wecomTenants.channel"), dataIndex: "channel", key: "channel" },
    {
      title: t("wecomTenants.activeSessions"),
      dataIndex: "session_count",
      key: "session_count",
      render: formatCompact,
    },
    {
      title: t("wecomTenants.userMessages"),
      dataIndex: "user_messages",
      key: "user_messages",
      render: formatCompact,
    },
    {
      title: t("wecomTenants.assistantMessages"),
      dataIndex: "assistant_messages",
      key: "assistant_messages",
      render: formatCompact,
    },
    {
      title: t("wecomTenants.totalMessages"),
      dataIndex: "total_messages",
      key: "total_messages",
      render: formatCompact,
    },
  ];

  const modelColumns: ColumnsType<ModelRow> = [
    { title: t("wecomTenants.provider"), dataIndex: "provider_id", key: "provider_id" },
    { title: t("wecomTenants.model"), dataIndex: "model", key: "model" },
    {
      title: t("wecomTenants.promptTokens"),
      dataIndex: "prompt_tokens",
      key: "prompt_tokens",
      render: formatCompact,
    },
    {
      title: t("wecomTenants.completionTokens"),
      dataIndex: "completion_tokens",
      key: "completion_tokens",
      render: formatCompact,
    },
    {
      title: t("wecomTenants.calls"),
      dataIndex: "call_count",
      key: "call_count",
      render: formatCompact,
    },
  ];

  const totalTokens =
    (tokens?.total_prompt_tokens ?? 0) + (tokens?.total_completion_tokens ?? 0);

  return (
    <div className={styles.tabContent}>
      <div className={styles.filters}>
        <DatePicker.RangePicker
          value={[startDate, endDate]}
          onChange={(dates) => {
            const nextStart = dates?.[0] || startDate;
            const nextEnd = dates?.[1] || endDate;
            setStartDate(nextStart);
            setEndDate(nextEnd);
          }}
        />
        <Select
          allowClear
          value={provider}
          placeholder={t("wecomTenants.providerFilter")}
          onChange={(value) => {
            setProvider(value);
            setModelName(undefined);
          }}
          style={{ minWidth: 160 }}
        >
          {providerOptions.map((item) => (
            <Select.Option key={item} value={item}>
              {item}
            </Select.Option>
          ))}
        </Select>
        <Select
          allowClear
          value={modelName}
          placeholder={t("wecomTenants.modelFilter")}
          onChange={setModelName}
          style={{ minWidth: 180 }}
        >
          {modelOptions.map((item) => (
            <Select.Option key={item} value={item}>
              {item}
            </Select.Option>
          ))}
        </Select>
        <Button type="primary" loading={loading} onClick={() => load()}>
          {t("common.refresh")}
        </Button>
      </div>

      {loading && !tokens ? (
        <div className={styles.tabLoading}>
          <Spinner />
        </div>
      ) : totalTokens === 0 && (stats?.total_messages ?? 0) === 0 ? (
        <Empty description={t("wecomTenants.noMonitoringData")} />
      ) : (
        <>
          <div className={styles.summaryMetrics}>
            <Card className={styles.metricCard}>
              <strong>{formatCompact(totalTokens)}</strong>
              <span>{t("wecomTenants.totalTokens")}</span>
            </Card>
            <Card className={styles.metricCard}>
              <strong>{formatCompact(tokens?.total_calls ?? 0)}</strong>
              <span>{t("wecomTenants.calls")}</span>
            </Card>
            <Card className={styles.metricCard}>
              <strong>{formatCompact(stats?.total_messages ?? 0)}</strong>
              <span>{t("wecomTenants.totalMessages")}</span>
            </Card>
            <Card className={styles.metricCard}>
              <strong>{formatCompact(stats?.total_active_sessions ?? 0)}</strong>
              <span>{t("wecomTenants.activeSessions")}</span>
            </Card>
          </div>

          <Card title={t("wecomTenants.activityTrend")}>
            <Column
              data={chartData}
              xField="date"
              yField="value"
              colorField="type"
              group
              height={210}
              autoFit
            />
          </Card>

          <Card title={t("wecomTenants.channelDistribution")} bodyStyle={{ padding: 0 }}>
            <Table<ChannelStats>
              columns={channelColumns}
              dataSource={stats?.channel_stats || []}
              rowKey="channel"
              pagination={false}
              size="small"
            />
          </Card>

          <Card title={t("wecomTenants.byModel")} bodyStyle={{ padding: 0 }}>
            <Table<ModelRow>
              columns={modelColumns}
              dataSource={modelRows}
              rowKey="key"
              pagination={false}
              size="small"
            />
          </Card>
        </>
      )}
    </div>
  );
}
