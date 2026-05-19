import { Button, Card, Empty, Table, Tag } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { formatCompact } from "../../../../utils/formatNumber";
import type { TenantRow } from "../model";

interface Props {
  rows: TenantRow[];
  onDrilldown?: (agentId: string) => void;
}

export function TenantStatusMatrix({ rows, onDrilldown }: Props) {
  const { t } = useTranslation();

  const healthColor = (status: TenantRow["health"]) => {
    if (status === "healthy") return "green";
    if (status === "degraded") return "orange";
    if (status === "unhealthy") return "red";
    return "default";
  };

  const healthLabel = (status: TenantRow["health"]) => {
    if (status === "healthy") return t("wecomTenantMonitoring.healthy");
    if (status === "degraded") return t("wecomTenantMonitoring.degraded");
    if (status === "unhealthy") return t("wecomTenantMonitoring.unhealthy");
    return "-";
  };

  const columns: ColumnsType<TenantRow> = [
    {
      title: t("wecomTenantMonitoring.tenant"),
      dataIndex: "tenantId",
      key: "tenantId",
      ellipsis: true,
    },
    {
      title: t("wecomTenantMonitoring.agent"),
      dataIndex: "agentName",
      key: "agentName",
      ellipsis: true,
    },
    {
      title: t("wecomTenantMonitoring.status"),
      key: "status",
      render: (_, row) => (
        <Tag color={row.running ? "green" : "default"}>
          {row.running
            ? t("wecomTenantMonitoring.running")
            : t("wecomTenantMonitoring.stopped")}
        </Tag>
      ),
    },
    {
      title: t("wecomTenantMonitoring.health"),
      key: "health",
      render: (_, row) => (
        <Tag color={healthColor(row.health)}>{healthLabel(row.health)}</Tag>
      ),
    },
    {
      title: t("wecomTenantMonitoring.tokens"),
      dataIndex: "tokens",
      key: "tokens",
      render: formatCompact,
    },
    {
      title: t("wecomTenantMonitoring.calls"),
      dataIndex: "calls",
      key: "calls",
      render: formatCompact,
    },
    {
      title: t("wecomTenantMonitoring.actions"),
      key: "actions",
      render: (_, row) => (
        <Button
          size="small"
          onClick={() => onDrilldown?.(row.agentId)}
        >
          {t("wecomTenantMonitoring.drilldown")}
        </Button>
      ),
    },
  ];

  return (
    <Card title={t("wecomTenantMonitoring.tenantMatrix")}>
      {rows.length === 0 ? (
        <Empty description={t("wecomTenantMonitoring.noTenants")} />
      ) : (
        <Table
          columns={columns}
          dataSource={rows}
          rowKey="key"
          pagination={false}
          size="small"
        />
      )}
    </Card>
  );
}
