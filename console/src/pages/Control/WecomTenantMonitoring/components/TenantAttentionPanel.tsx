import { Button, Card, Empty, Table, Tag } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import type { AttentionItem } from "../model";

interface Props {
  items: AttentionItem[];
  onDrilldown?: (agentId: string) => void;
}

export function TenantAttentionPanel({ items, onDrilldown }: Props) {
  const { t } = useTranslation();

  const severityColor = (severity: AttentionItem["severity"]) => {
    if (severity === "error") return "red";
    if (severity === "warning") return "orange";
    return "blue";
  };

  const reasonLabel = (reason: string) => {
    const key = `wecomTenantMonitoring.${reason}` as string;
    return t(key);
  };

  const columns: ColumnsType<AttentionItem> = [
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
      key: "severity",
      render: (_, item) => (
        <Tag color={severityColor(item.severity)}>
          {reasonLabel(item.reason)}
        </Tag>
      ),
    },
    {
      title: t("wecomTenantMonitoring.actions"),
      key: "actions",
      render: (_, item) => (
        <Button
          size="small"
          onClick={() => onDrilldown?.(item.agentId)}
        >
          {t("wecomTenantMonitoring.drilldown")}
        </Button>
      ),
    },
  ];

  return (
    <Card title={t("wecomTenantMonitoring.attentionList")}>
      {items.length === 0 ? (
        <Empty description={t("wecomTenantMonitoring.noAttention")} />
      ) : (
        <Table
          columns={columns}
          dataSource={items}
          rowKey="key"
          pagination={false}
          size="small"
        />
      )}
    </Card>
  );
}
