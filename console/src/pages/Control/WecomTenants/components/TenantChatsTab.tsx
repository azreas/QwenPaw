import { useEffect, useMemo, useState } from "react";
import { Alert, Collapse, Drawer, Empty, Spinner, Tag } from "@agentscope-ai/design";
import { Button, Input, Table } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { WecomTenantChatListResponse } from "../../../../api/types";
import styles from "../index.module.less";

interface Props {
  agentId: string;
}

interface ChatRow {
  key: string;
  session_id: string;
  channel: string;
  updated_at?: string;
  raw: Record<string, unknown>;
}

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

function toChatRow(item: Record<string, unknown>, index: number): ChatRow {
  const sessionId =
    item.session_id || item.id || item.chat_id || item.user_id || `row_${index}`;
  return {
    key: String(sessionId),
    session_id: String(sessionId),
    channel: asText(item.channel),
    updated_at: asText(item.updated_at || item.last_message_at || item.created_at),
    raw: item,
  };
}

function asMessages(value: Record<string, unknown> | null): MessageItem[] {
  const messages = value?.messages;
  return Array.isArray(messages) ? (messages as MessageItem[]) : [];
}

function renderContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((item) =>
        typeof item === "string" ? item : JSON.stringify(item, null, 2),
      )
      .join("\n");
  }
  return content === undefined || content === null
    ? "-"
    : JSON.stringify(content, null, 2);
}

export function TenantChatsTab({ agentId }: Props) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [channel, setChannel] = useState("");
  const [data, setData] = useState<WecomTenantChatListResponse | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<Record<string, unknown> | null>(
    null,
  );

  const load = async (
    nextPage = page,
    nextPageSize = pageSize,
    nextChannel = channel,
  ) => {
    setLoading(true);
    try {
      setData(
        await wecomTenantApi.listWecomTenantChats(agentId, {
          page: nextPage,
          page_size: nextPageSize,
          channel: nextChannel.trim() || undefined,
        }),
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, page, pageSize]);

  const rows = useMemo(
    () => (data?.items || []).map((item, index) => toChatRow(item, index)),
    [data?.items],
  );

  const openSession = async (row: ChatRow) => {
    setDrawerOpen(true);
    setDrawerLoading(true);
    setDrawerError(null);
    setSessionData(null);
    try {
      const detail = await wecomTenantApi.getWecomTenantChatSession(
        agentId,
        row.session_id,
      );
      setSessionData(detail);
    } catch (error) {
      const message = (error as Error).message || "";
      setDrawerError(
        message.includes("404") || message.includes("not found")
          ? t("wecomTenants.sessionMissing")
          : message,
      );
    } finally {
      setDrawerLoading(false);
    }
  };

  const applyChannelFilter = () => {
    setPage(1);
    load(1, pageSize, channel);
  };

  const columns: ColumnsType<ChatRow> = [
    {
      title: t("wecomTenants.sessionId"),
      dataIndex: "session_id",
      key: "session_id",
      render: (value: string) => <code>{value}</code>,
    },
    { title: t("wecomTenants.channel"), dataIndex: "channel", key: "channel" },
    {
      title: t("wecomTenants.updatedAt"),
      dataIndex: "updated_at",
      key: "updated_at",
    },
    {
      title: t("wecomTenants.actions"),
      key: "actions",
      render: (_, row) => (
        <Button size="small" onClick={() => openSession(row)}>
          {t("common.view")}
        </Button>
      ),
    },
  ];

  if (loading && !data) {
    return (
      <div className={styles.tabLoading}>
        <Spinner />
      </div>
    );
  }

  return (
    <div className={styles.tabContent}>
      <div className={styles.filters}>
        <Input
          value={channel}
          onChange={(event) => setChannel(event.target.value)}
          placeholder={t("wecomTenants.channelFilter")}
        />
        <Button loading={loading} onClick={applyChannelFilter}>
          {t("common.refresh")}
        </Button>
      </div>
      {rows.length ? (
        <Table<ChatRow>
          columns={columns}
          dataSource={rows}
          rowKey="key"
          loading={loading}
          size="small"
          pagination={{
            current: data?.page || page,
            pageSize: data?.page_size || pageSize,
            total: data?.total || 0,
            showSizeChanger: true,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage);
              setPageSize(nextPageSize);
            },
          }}
        />
      ) : (
        <Empty description={t("wecomTenants.noChats")} />
      )}
      <Drawer
        title={t("wecomTenants.chatDetail")}
        open={drawerOpen}
        width={720}
        onClose={() => setDrawerOpen(false)}
      >
        {drawerLoading ? (
          <div className={styles.tabLoading}>
            <Spinner />
          </div>
        ) : drawerError ? (
          <Alert type="warning" showIcon message={drawerError} />
        ) : (
          <>
            <div className={styles.messageList}>
              {asMessages(sessionData).length ? (
                asMessages(sessionData).map((item, index) => (
                  <div className={styles.messageItem} key={`${item.role}-${index}`}>
                    <div className={styles.messageMeta}>
                      <Tag>{item.role || "message"}</Tag>
                      <span>{asText(item.created_at || item.timestamp)}</span>
                      {item.tokens !== undefined && (
                        <span>tokens: {asText(item.tokens)}</span>
                      )}
                    </div>
                    <pre className={styles.messageContent}>
                      {renderContent(item.content)}
                    </pre>
                  </div>
                ))
              ) : (
                <Empty description={t("wecomTenants.noMessages")} />
              )}
            </div>
            <Collapse
              items={[
                {
                  key: "raw",
                  label: t("wecomTenants.rawJson"),
                  children: (
                    <pre className={styles.jsonPreview}>
                      {JSON.stringify(sessionData, null, 2)}
                    </pre>
                  ),
                },
              ]}
            />
          </>
        )}
      </Drawer>
    </div>
  );
}
