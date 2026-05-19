import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  Button,
  DatePicker,
  Spin,
  Empty,
  Statistic,
  Table,
  Row,
  Col,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import dayjs, { Dayjs } from "dayjs";
import { useTheme } from "../../../contexts/ThemeContext";
import { tokenUsageApi, TokenUsageSummary, TokenUsageStats } from "../../../api/modules/tokenUsage";
import type { ColumnsType } from "antd/es/table";

type ByModelRow = TokenUsageStats & { key: string };
type ByDateRow = TokenUsageStats & { key: string; date: string };

const formatCompact = (num: number): string => {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
};

export default function TokenUsagePage() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<TokenUsageSummary | null>(null);
  const [startDate, setStartDate] = useState<Dayjs>(dayjs().subtract(30, "day"));
  const [endDate, setEndDate] = useState<Dayjs>(dayjs());

  const fetchData = async () => {
    setLoading(true);
    try {
      const summary = await tokenUsageApi.getTokenUsage({
        start_date: startDate.format("YYYY-MM-DD"),
        end_date: endDate.format("YYYY-MM-DD"),
      });
      setData(summary);
    } catch (error) {
      console.error("Failed to load token usage:", error);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDateChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates?.[0]) setStartDate(dates[0]);
    if (dates?.[1]) setEndDate(dates[1]);
  };

  const byModelDataSource: ByModelRow[] = useMemo(() => {
    if (!data?.by_model) return [];
    return Object.entries(data.by_model).map(([key, stats]) => ({
      ...stats,
      key,
    }));
  }, [data?.by_model]);

  const byDateDataSource: ByDateRow[] = useMemo(() => {
    if (!data?.by_date) return [];
    return Object.entries(data.by_date).map(([dt, stats]) => ({
      ...stats,
      key: dt,
      date: dt,
    }));
  }, [data?.by_date]);

  const byModelColumns: ColumnsType<ByModelRow> = useMemo(
    () => [
      {
        title: t("tokenUsage.provider"),
        dataIndex: "provider_id",
        key: "provider_id",
        render: (v: string) => v || "-",
      },
      {
        title: t("tokenUsage.model"),
        dataIndex: "model",
        key: "model",
        render: (v: string, r) => v || r.key,
      },
      {
        title: t("tokenUsage.promptTokens"),
        dataIndex: "prompt_tokens",
        key: "prompt_tokens",
        render: (n: number) => formatCompact(n),
      },
      {
        title: t("tokenUsage.completionTokens"),
        dataIndex: "completion_tokens",
        key: "completion_tokens",
        render: (n: number) => formatCompact(n),
      },
      {
        title: t("tokenUsage.totalCalls"),
        dataIndex: "call_count",
        key: "call_count",
        render: (n: number) => formatCompact(n),
      },
    ],
    [t]
  );

  const byDateColumns: ColumnsType<ByDateRow> = useMemo(
    () => [
      { title: t("tokenUsage.date"), dataIndex: "date", key: "date" },
      {
        title: t("tokenUsage.promptTokens"),
        dataIndex: "prompt_tokens",
        key: "prompt_tokens",
        render: (n: number) => formatCompact(n),
      },
      {
        title: t("tokenUsage.completionTokens"),
        dataIndex: "completion_tokens",
        key: "completion_tokens",
        render: (n: number) => formatCompact(n),
      },
      {
        title: t("tokenUsage.totalCalls"),
        dataIndex: "call_count",
        key: "call_count",
        render: (n: number) => formatCompact(n),
      },
    ],
    [t]
  );

  return (
    <div style={{ padding: "24px", height: "100%", overflow: "auto" }}>
      <Card
        style={{
          background: isDark ? "#1f1f1f" : "#fff",
          borderColor: isDark ? "#303030" : "#f0f0f0",
        }}
        styles={{
          header: {
            padding: "16px 24px",
            borderBottom: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "#f0f0f0"}`,
          },
          body: { padding: "24px" },
        }}
        title={t("nav.tokenUsage")}
        extra={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <DatePicker.RangePicker
              value={[startDate, endDate]}
              onChange={handleDateChange}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchData}
              loading={loading}
            >
              {t("tokenUsage.refresh")}
            </Button>
          </div>
        }
      >
        <Spin spinning={loading}>
          {data && data.total_calls > 0 ? (
            <>
              <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col span={8}>
                  <Card
                    style={{
                      background: isDark ? "#141414" : "#fafafa",
                      borderColor: isDark ? "#303030" : "#f0f0f0",
                    }}
                  >
                    <Statistic
                      title={t("tokenUsage.promptTokens")}
                      value={data.total_prompt_tokens}
                      groupSeparator=","
                      valueStyle={{ color: "#1890ff" }}
                    />
                  </Card>
                </Col>
                <Col span={8}>
                  <Card
                    style={{
                      background: isDark ? "#141414" : "#fafafa",
                      borderColor: isDark ? "#303030" : "#f0f0f0",
                    }}
                  >
                    <Statistic
                      title={t("tokenUsage.completionTokens")}
                      value={data.total_completion_tokens}
                      groupSeparator=","
                      valueStyle={{ color: "#52c41a" }}
                    />
                  </Card>
                </Col>
                <Col span={8}>
                  <Card
                    style={{
                      background: isDark ? "#141414" : "#fafafa",
                      borderColor: isDark ? "#303030" : "#f0f0f0",
                    }}
                  >
                    <Statistic
                      title={t("tokenUsage.totalCalls")}
                      value={data.total_calls}
                      groupSeparator=","
                      valueStyle={{ color: "#faad14" }}
                    />
                  </Card>
                </Col>
              </Row>

              {byModelDataSource.length > 0 && (
                <Card
                  title={t("tokenUsage.byModel")}
                  style={{
                    marginBottom: 16,
                    background: isDark ? "#141414" : "#fafafa",
                    borderColor: isDark ? "#303030" : "#f0f0f0",
                  }}
                >
                  <Table<ByModelRow>
                    columns={byModelColumns}
                    dataSource={byModelDataSource}
                    rowKey="key"
                    pagination={false}
                    size="small"
                  />
                </Card>
              )}

              {byDateDataSource.length > 0 && (
                <Card
                  title={t("tokenUsage.byDate")}
                  style={{
                    background: isDark ? "#141414" : "#fafafa",
                    borderColor: isDark ? "#303030" : "#f0f0f0",
                  }}
                >
                  <Table<ByDateRow>
                    columns={byDateColumns}
                    dataSource={byDateDataSource}
                    rowKey="key"
                    pagination={{ pageSize: 10 }}
                    size="small"
                  />
                </Card>
              )}
            </>
          ) : (
            <Empty description={t("tokenUsage.noData")} />
          )}
        </Spin>
      </Card>
    </div>
  );
}
