import { useEffect, useState } from "react";
import { Button, Card, Input, Modal, Select, Switch, Table, Tag } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { authApi } from "../../../api/modules/auth";
import type { ConsoleUser, CreateUserRequest } from "../../../api/types/auth";
import { ROLE_LABELS } from "./userModel";
import { useAppMessage } from "../../../hooks/useAppMessage";

export default function UsersPage() {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [users, setUsers] = useState<ConsoleUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRoles, setNewRoles] = useState<string[]>(["tenant_member"]);
  const [newTenantId, setNewTenantId] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await authApi.listUsers();
      setUsers(res.items || []);
    } catch {
      message.error(t("common.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createUser = async () => {
    setSaving(true);
    try {
      const body: CreateUserRequest = {
        username: newUsername,
        password: newPassword,
        roles: newRoles,
        tenant_id: newTenantId,
      };
      await authApi.createUser(body);
      await load();
      setCreateOpen(false);
      setNewUsername("");
      setNewPassword("");
      setNewRoles(["tenant_member"]);
      setNewTenantId("");
      message.success(t("platform.userCreated"));
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const toggleDisabled = async (user: ConsoleUser) => {
    try {
      await authApi.updateUser(user.username, { disabled: !user.disabled });
      await load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const columns: ColumnsType<ConsoleUser> = [
    {
      title: t("platform.username"),
      dataIndex: "username",
      key: "username",
    },
    {
      title: t("platform.roles"),
      dataIndex: "roles",
      key: "roles",
      render: (roles: string[]) => (
        <div style={{ display: "flex", gap: 4 }}>
          {(roles || []).map((r) => (
            <Tag key={r}>{ROLE_LABELS[r] || r}</Tag>
          ))}
        </div>
      ),
    },
    {
      title: t("platform.tenantId"),
      dataIndex: "tenant_id",
      key: "tenant_id",
    },
    {
      title: t("platform.disabled"),
      key: "disabled",
      width: 100,
      render: (_, user) => (
        <Switch
          checked={!user.disabled}
          onChange={() => toggleDisabled(user)}
        />
      ),
    },
  ];

  const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({
    label,
    value,
  }));

  return (
    <Card
      title={t("platform.users")}
      extra={
        <Button type="primary" onClick={() => setCreateOpen(true)}>
          {t("common.create")}
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={users}
        rowKey="username"
        loading={loading}
        pagination={false}
        size="small"
      />
      <Modal
        title={t("platform.createUser")}
        open={createOpen}
        onOk={createUser}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={saving}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Input
            placeholder={t("platform.username")}
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
          />
          <Input.Password
            placeholder={t("platform.password")}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <Select
            mode="multiple"
            value={newRoles}
            onChange={setNewRoles}
            options={roleOptions}
            style={{ width: "100%" }}
          />
          <Input
            placeholder={t("platform.tenantId")}
            value={newTenantId}
            onChange={(e) => setNewTenantId(e.target.value)}
          />
        </div>
      </Modal>
    </Card>
  );
}
