import { useMemo } from "react";
import { Card, Switch, Table } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../../api/modules/wecomTenant";
import type { WecomTenantTool } from "../../../../../api/types";

interface Props {
  agentId: string;
  tools: WecomTenantTool[];
  loading: boolean;
  onRefresh: () => Promise<void>;
}

export function TenantToolsSection({
  agentId,
  tools,
  loading,
  onRefresh,
}: Props) {
  const { t } = useTranslation();
  const columns: ColumnsType<WecomTenantTool> = useMemo(
    () => [
      { title: t("wecomTenants.name"), dataIndex: "name", key: "name" },
      {
        title: t("wecomTenants.enabled"),
        key: "enabled",
        render: (_, tool) => (
          <Switch
            checked={tool.enabled}
            onChange={async () => {
              await wecomTenantApi.toggleWecomTenantTool(agentId, tool.name);
              await onRefresh();
            }}
          />
        ),
      },
      {
        title: t("wecomTenants.asyncExecution"),
        key: "async_execution",
        render: (_, tool) => (
          <Switch
            checked={tool.async_execution}
            disabled={!tool.enabled}
            onChange={async (checked) => {
              await wecomTenantApi.updateWecomTenantToolAsyncExecution(
                agentId,
                tool.name,
                { async_execution: checked },
              );
              await onRefresh();
            }}
          />
        ),
      },
    ],
    [agentId, onRefresh, t],
  );

  return (
    <Card title={t("wecomTenants.tools")} bodyStyle={{ padding: 0 }}>
      <Table
        columns={columns}
        dataSource={tools}
        rowKey="name"
        loading={loading}
        pagination={false}
        size="small"
      />
    </Card>
  );
}
