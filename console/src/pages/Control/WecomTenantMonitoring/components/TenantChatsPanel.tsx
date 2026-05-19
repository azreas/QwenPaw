import { useState } from "react";
import { Alert, Button, Card, Collapse, Drawer, Empty, Spinner, Table, Tag } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { WecomTenantChatListResponse } from "../../../../api/types/wecomTenant";

type ChatRow = Record<string, unknown> & { key: string };

interface MessageItem {
  role?: string;
  content?: unknown;
  created_at?: string;
  timestamp?: string;
  tokens?: unknown;
}

function asText(value: unknown): string {
  return value === undefined || value === null ? "-" : String(value);
}

function asMessages(value: Record<string, unknown> | null): MessageItem[] {
  const messages = value?.messages;
  return Array.isArray(messages) ? (messages as MessageItem[]) : [];
}

interface Props {
  agentId: string;
  chats: WecomTenantChatListResponse | null;
}

export function TenantChatsPanel({ agentId, chats }: Props) {
  const { t } = useTranslation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<Record<string, unknown> | null>(null);

  const rows: ChatRow[] = (chats?.items || []).map(
    (item, index) => ({
      ...item,
      key: String(item.session_id || item.id || index),
    }),
  );

  const openSession = async (row: ChatRow) => {
    const sessionId = String(row.session_id || row.id || row.key);
    setDrawerOpen(true);
    setDrawerLoading(true);
    setDrawerError(null);
    setSessionData(null);
    try {
      const detail = await wecomTenantApi.getWecomTenantChatSession(agentId, sessionId);
      setSessionData(detail);
    } catch (err) {
      const msg = (err as Error).message || "";
      setDrawerError(
        msg.includes("404") || msg.includes("not found")
          ? t("wecomTenants.sessionMissing")
          : msg || t("wecomTenantMonitoring.loadFailed"),
      );
    } finally {
      setDrawerLoading(false);
    }
  };

  const messages = asMessages(sessionData);

  const columns: ColumnsType<ChatRow> = [
    {
      title: t("wecomTenants.sessionId"),
      key: "session",
      render: (_, row) => String(row.session_id || row.id || row.key),
    },
    {
      title: t("wecomTenantMonitoring.updatedAt"),
      key: "updated_at",
      render: (_, row) => String(row.updated_at || row.created_at || "-"),
    },
    {
      title: t("wecomTenantMonitoring.actions"),
      key: "actions",
      render: (_, row) => (
        <Button size="small" onClick={() => openSession(row)}>
          {t("wecomTenantMonitoring.viewSession")}
        </Button>
      ),
    },
  ];

  return (
    <>
      <Card
        title={t("wecomTenantMonitoring.chatDiagnosis")}
        bodyStyle={{ padding: 0 }}
      >
        {rows.length ? (
          <Table columns={columns} dataSource={rows} pagination={false} rowKey="key" />
        ) : (
          <Empty description={t("wecomTenants.noChats")} />
        )}
      </Card>
      <Drawer
        title={t("wecomTenantMonitoring.chatDiagnosis")}
        open={drawerOpen}
        width={720}
        onClose={() => setDrawerOpen(false)}
      >
        {drawerLoading ? (
          <div style={{ textAlign: "center", padding: 24 }}>
            <Spinner />
          </div>
        ) : drawerError ? (
          <Alert type="warning" showIcon message={drawerError} />
        ) : (
          <>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {messages.length ? (
                messages.map((msg, idx) => (
                  <div key={idx} style={{ padding: "8px 12px", background: msg.role === "user" ? "#f0f5ff" : "#f6ffed", borderRadius: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <Tag>{msg.role || "message"}</Tag>
                      <span style={{ fontSize: 12, color: "rgba(0,0,0,0.45)" }}>{asText(msg.created_at || msg.timestamp)}</span>
                    </div>
                    <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                      {typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content, null, 2)}
                    </pre>
                  </div>
                ))
              ) : (
                <Empty description={t("wecomTenants.noMessages")} />
              )}
            </div>
            {sessionData && (
              <Collapse
                style={{ marginTop: 16 }}
                items={[
                  {
                    key: "raw",
                    label: t("wecomTenants.rawJson"),
                    children: (
                      <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>
                        {JSON.stringify(sessionData, null, 2)}
                      </pre>
                    ),
                  },
                ]}
              />
            )}
          </>
        )}
      </Drawer>
    </>
  );
}
