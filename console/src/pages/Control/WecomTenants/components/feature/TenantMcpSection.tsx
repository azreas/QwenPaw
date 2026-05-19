import { useMemo, useState } from "react";
import { Button, Card, Modal, Switch, Table, Tag, Tooltip } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../../api/modules/wecomTenant";
import type { WecomTenantMcpClient } from "../../../../../api/types";
import { useAppMessage } from "../../../../../hooks/useAppMessage";
import styles from "../../index.module.less";
import { TenantMcpClientModal } from "./TenantMcpClientModal";

interface Props {
  agentId: string;
  clients: WecomTenantMcpClient[];
  loading: boolean;
  onRefresh: () => Promise<void>;
}

export function TenantMcpSection({
  agentId,
  clients,
  loading,
  onRefresh,
}: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<WecomTenantMcpClient | null>(null);

  const openCreate = () => {
    setEditingClient(null);
    setModalOpen(true);
  };

  const openEdit = (client: WecomTenantMcpClient) => {
    setEditingClient(client);
    setModalOpen(true);
  };

  const deleteClient = (client: WecomTenantMcpClient) => {
    Modal.confirm({
      title: t("wecomTenants.deleteMcpTitle", { name: client.client_key }),
      content: t("wecomTenants.deleteMcpContent", {
        name: client.client_key,
        agentId,
      }),
      okText: t("common.delete"),
      okType: "danger",
      cancelText: t("common.cancel"),
      onOk: async () => {
        await wecomTenantApi.deleteWecomTenantMcp(agentId, client.client_key);
        message.success(t("wecomTenants.configSavedReloaded"));
        await onRefresh();
      },
    });
  };

  const columns: ColumnsType<WecomTenantMcpClient> = useMemo(
    () => [
      {
        title: t("wecomTenants.name"),
        key: "name",
        render: (_, client) => (
          <div className={styles.tenantIdentity}>
            <strong>{client.client_key}</strong>
            <span>{client.description || client.name || "-"}</span>
          </div>
        ),
      },
      {
        title: t("wecomTenants.transport"),
        dataIndex: "transport",
        key: "transport",
        width: 130,
      },
      {
        title: t("wecomTenants.mcpSecrets"),
        key: "secrets",
        render: (_, client) => (
          <div className={styles.rowActions}>
            <Tag>env {Object.keys(client.env || {}).length}</Tag>
            <Tag>headers {Object.keys(client.headers || {}).length}</Tag>
          </div>
        ),
      },
      {
        title: t("wecomTenants.enabled"),
        key: "enabled",
        width: 90,
        render: (_, client) => (
          <Switch
            checked={client.enabled}
            onChange={async () => {
              await wecomTenantApi.toggleWecomTenantMcp(agentId, client.client_key);
              await onRefresh();
            }}
          />
        ),
      },
      {
        title: t("wecomTenants.lastTest"),
        key: "last_test",
        width: 130,
        render: (_, client) => {
          if (!client.last_test_status) return <Tag>-</Tag>;
          const color = client.last_test_status === "ok" ? "green" : "red";
          const tip = client.last_test_detail || "";
          return (
            <Tooltip title={tip}>
              <Tag color={color}>{client.last_test_status}</Tag>
            </Tooltip>
          );
        },
      },
      {
        title: t("wecomTenants.lastCall"),
        key: "last_call",
        width: 120,
        render: (_, client) => {
          if (!client.last_call_status) return <Tag>-</Tag>;
          const color = client.last_call_status === "success" ? "green" : "red";
          return <Tag color={color}>{client.last_call_status}</Tag>;
        },
      },
      {
        title: t("wecomTenants.actions"),
        key: "actions",
        width: 150,
        render: (_, client) => (
          <div className={styles.rowActions}>
            <Button size="small" onClick={() => openEdit(client)}>
              {t("common.edit")}
            </Button>
            <Button size="small" danger onClick={() => deleteClient(client)}>
              {t("common.delete")}
            </Button>
          </div>
        ),
      },
    ],
    [agentId, onRefresh, t],
  );

  return (
    <Card
      title={t("wecomTenants.mcp")}
      bodyStyle={{ padding: 0 }}
      extra={<Button onClick={openCreate}>{t("common.create")}</Button>}
    >
      <Table
        columns={columns}
        dataSource={clients}
        rowKey="client_key"
        loading={loading}
        pagination={false}
        size="small"
        scroll={{ x: 760 }}
      />
      <TenantMcpClientModal
        agentId={agentId}
        open={modalOpen}
        client={editingClient}
        onClose={() => setModalOpen(false)}
        onSaved={onRefresh}
      />
    </Card>
  );
}
