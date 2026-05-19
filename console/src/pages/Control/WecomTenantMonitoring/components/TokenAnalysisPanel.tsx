import { Card, Empty, Table, Select } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { formatCompact } from "../../../../utils/formatNumber";
import type { TokenModelRow, TokenDateRow } from "../model";

interface Props {
  modelRows: TokenModelRow[];
  dateRows: TokenDateRow[];
}

type TabKey = "model" | "date";

export function TokenAnalysisPanel({ modelRows, dateRows }: Props) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<TabKey>("model");

  const modelColumns: ColumnsType<TokenModelRow> = [
    { title: t("wecomTenantMonitoring.model"), dataIndex: "model", key: "model" },
    {
      title: t("wecomTenantMonitoring.promptTokens"),
      dataIndex: "promptTokens",
      key: "promptTokens",
      render: formatCompact,
    },
    {
      title: t("wecomTenantMonitoring.completionTokens"),
      dataIndex: "completionTokens",
      key: "completionTokens",
      render: formatCompact,
    },
    {
      title: t("wecomTenantMonitoring.calls"),
      dataIndex: "callCount",
      key: "callCount",
      render: formatCompact,
    },
  ];

  const dateColumns: ColumnsType<TokenDateRow> = [
    { title: t("wecomTenantMonitoring.date"), dataIndex: "date", key: "date" },
    {
      title: t("wecomTenantMonitoring.promptTokens"),
      dataIndex: "promptTokens",
      key: "promptTokens",
      render: formatCompact,
    },
    {
      title: t("wecomTenantMonitoring.completionTokens"),
      dataIndex: "completionTokens",
      key: "completionTokens",
      render: formatCompact,
    },
    {
      title: t("wecomTenantMonitoring.calls"),
      dataIndex: "callCount",
      key: "callCount",
      render: formatCompact,
    },
  ];

  const isEmpty = tab === "model" ? modelRows.length === 0 : dateRows.length === 0;

  return (
    <Card
      title={t("wecomTenantMonitoring.tokenAnalysis")}
      extra={
        <Select
          value={tab}
          onChange={(v: string) => setTab(v as TabKey)}
          style={{ minWidth: 100 }}
        >
          <Select.Option value="model">{t("wecomTenantMonitoring.byModel")}</Select.Option>
          <Select.Option value="date">{t("wecomTenantMonitoring.byDate")}</Select.Option>
        </Select>
      }
    >
      {isEmpty ? (
        <Empty description={t("wecomTenantMonitoring.noTokenData")} />
      ) : tab === "model" ? (
        <Table
          columns={modelColumns}
          dataSource={modelRows}
          rowKey="key"
          pagination={false}
          size="small"
        />
      ) : (
        <Table
          columns={dateColumns}
          dataSource={dateRows}
          rowKey="key"
          pagination={false}
          size="small"
        />
      )}
    </Card>
  );
}
