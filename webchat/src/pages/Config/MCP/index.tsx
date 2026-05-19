import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  Button,
  Switch,
  Typography,
  Spin,
  message,
  Modal,
  Input,
  Form,
  Select,
  Empty,
  Tag,
  Popconfirm,
  Tooltip,
  Breadcrumb,
} from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
  ApiOutlined,
} from "@ant-design/icons";
import { agentApi } from "../../../api/modules/agent";

const { Text, Paragraph } = Typography;

const { Option } = Select;

type MCPTransport = "stdio" | "streamable_http" | "sse";

export interface MCPClientInfo {
  key: string;
  name: string;
  description?: string;
  enabled: boolean;
  transport: "stdio" | "streamable_http" | "sse";
  url?: string;
  headers?: Record<string, string>;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
  tools?: MCPToolInfo[];
  isConnected?: boolean;
  error?: string;
}

export interface MCPToolInfo {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

export default function MCPConfig() {
  const { t } = useTranslation();
  const [clients, setClients] = useState<MCPClientInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const loadClients = useCallback(async () => {
    setLoading(true);
    try {
      const config = await agentApi.getConfig();
      // Transform MCP clients from agent config to match UI expectations
      const transformedClients = config.mcp_clients.map((c: any) => ({
        key: c.name,
        name: c.display_name || c.name,
        description: c.description || "",
        enabled: c.enabled,
        transport: c.transport || "stdio",
        url: c.url || "",
        command: c.command || "",
        args: c.args || [],
        env: c.env || {},
        cwd: c.cwd || "",
        isConnected: false, // Not available in webchat backend
      }));
      setClients(transformedClients);
    } catch (error) {
      console.error("Failed to load MCP clients:", error);
      message.error(t("common.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadClients();
  }, [loadClients]);

  const handleToggleClient = async (client: MCPClientInfo) => {
    try {
      await agentApi.toggleMCP(client.key, !client.enabled);
      message.success(t("common.success"));
      loadClients();
    } catch (error) {
      console.error("Failed to toggle MCP client:", error);
      message.error(t("common.error"));
    }
  };

  const handleDeleteClient = async (_clientKey: string) => {
    // Note: Backend doesn't have a delete MCP client endpoint for webchat
    message.warning(t("mcp.deleteNotSupported"));
  };

  const handleCreateClient = () => {
    // Note: Backend doesn't have create MCP client endpoint for webchat
    message.warning(t("mcp.createNotSupported"));
  };

  const handleEditClient = (_client: MCPClientInfo) => {
    // Note: Backend doesn't have edit MCP client endpoint for webchat
    message.warning(t("mcp.editNotSupported"));
  };

  const handleSaveClient = async (_values: {
    key: string;
    name?: string;
    description?: string;
    transport: MCPTransport;
    url?: string;
    command?: string;
    args?: string;
    env?: Record<string, string>;
    cwd?: string;
    enabled?: boolean;
  }) => {
    // Note: Backend doesn't have save MCP client endpoint for webchat
    message.warning(t("mcp.editNotSupported"));
  };

  const getTransportLabel = (transport: string) => {
    switch (transport) {
      case "stdio":
        return "STDIO";
      case "streamable_http":
        return "HTTP";
      case "sse":
        return "SSE";
      default:
        return transport;
    }
  };

  return (
    <div style={{ padding: "24px", height: "100%", overflow: "auto" }}>
      {/* 面包屑导航 */}
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: t("config.workspace") },
          { title: t("config.mcp") },
        ]}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", gap: 8 }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadClients}
            loading={loading}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreateClient}
          >
            {t("common.create")}
          </Button>
        </div>
      </div>

      <Spin spinning={loading}>
        {clients.length === 0 ? (
          <Empty description={t("common.noData")} />
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
              gap: 16,
            }}
          >
            {clients.map((client) => (
              <Card
                key={client.key}
                hoverable
              >
                <div style={{ marginBottom: 12 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 8,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <ApiOutlined style={{ fontSize: 24, color: "#1890ff" }} />
                      <Text strong style={{ fontSize: 16 }}>
                        {client.name || client.key}
                      </Text>
                    </div>
                    <Switch
                      checked={client.enabled}
                      onChange={() => handleToggleClient(client)}
                      size="small"
                    />
                  </div>

                  <div style={{ marginBottom: 8 }}>
                    <Tag>{getTransportLabel(client.transport)}</Tag>
                    {client.isConnected ? (
                      <Tag color="success" style={{ marginLeft: 4 }}>
                        {t("mcp.connected")}
                      </Tag>
                    ) : (
                      <Tag color="error" style={{ marginLeft: 4 }}>
                        {t("mcp.disconnected")}
                      </Tag>
                    )}
                  </div>

                  <Paragraph
                    ellipsis={{ rows: 3 }}
                    style={{
                      color: "#666",
                      fontSize: 14,
                      marginBottom: 12,
                    }}
                  >
                    {client.description || client.command || client.url || "-"}
                  </Paragraph>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: 8,
                    }}
                  >
                    <Tooltip title={t("common.edit")}>
                      <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEditClient(client)}
                      />
                    </Tooltip>
                    <Popconfirm
                      title={t("common.confirmDelete")}
                      onConfirm={() => handleDeleteClient(client.key)}
                      okText={t("common.yes")}
                      cancelText={t("common.no")}
                    >
                      <Tooltip title={t("common.delete")}>
                        <Button
                          type="text"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                        />
                      </Tooltip>
                    </Popconfirm>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Spin>

      <Modal
        title={
          false ? t("mcp.editClient") : t("mcp.createClient")
        }
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveClient}
          initialValues={{ transport: "stdio", enabled: true }}
        >
          <Form.Item
            name="key"
            label={t("mcp.key")}
            rules={[{ required: true, message: t("common.required") }]}
          >
            <Input disabled={false} />
          </Form.Item>
          <Form.Item name="name" label={t("mcp.name")}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label={t("mcp.description")}>
            <Input />
          </Form.Item>
          <Form.Item
            name="transport"
            label={t("mcp.transport")}
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="stdio">STDIO</Option>
              <Option value="streamable_http">HTTP</Option>
              <Option value="sse">SSE</Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.transport !== currentValues.transport
            }
          >
            {({ getFieldValue }) => {
              const transport = getFieldValue("transport");
              return transport === "stdio" ? (
                <>
                  <Form.Item name="command" label={t("mcp.command")}>
                    <Input placeholder="npx" />
                  </Form.Item>
                  <Form.Item name="args" label={t("mcp.args")}>
                    <Input placeholder="-y @modelcontextprotocol/server-filesystem" />
                  </Form.Item>
                  <Form.Item name="cwd" label={t("mcp.cwd")}>
                    <Input />
                  </Form.Item>
                </>
              ) : (
                <Form.Item name="url" label={t("mcp.url")}>
                  <Input placeholder="http://localhost:3000" />
                </Form.Item>
              );
            }}
          </Form.Item>

          <Form.Item name="enabled" valuePropName="checked">
            <Switch checkedChildren={t("common.enabled")} unCheckedChildren={t("common.disabled")} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
