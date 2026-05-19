import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  Switch,
  List,
  Spin,
  message,
  Tabs,
  Typography,
} from "antd";
import {
  SettingOutlined,
  ToolOutlined,
  ApiOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useTheme } from "../../../../contexts/ThemeContext";
import { agentApi, AgentConfig } from "../../../../api/modules/agent";

const { Title, Text } = Typography;

export default function ConfigPage() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [loading, setLoading] = useState(false);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const data = await agentApi.getConfig();
      setConfig(data);
    } catch (error) {
      console.error("Failed to load agent config:", error);
      message.error(t("common.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleToggleTool = async (toolName: string, enabled: boolean) => {
    try {
      await agentApi.toggleTool(toolName, enabled);
      setConfig((prev) =>
        prev
          ? {
            ...prev,
            tools: prev.tools.map((tool) =>
              tool.name === toolName ? { ...tool, enabled } : tool
            ),
          }
          : null
      );
      message.success(t("common.success"));
    } catch {
      message.error(t("common.error"));
    }
  };

  const handleToggleMCP = async (clientName: string, enabled: boolean) => {
    try {
      await agentApi.toggleMCP(clientName, enabled);
      setConfig((prev) =>
        prev
          ? {
            ...prev,
            mcp_clients: prev.mcp_clients.map((client) =>
              client.name === clientName ? { ...client, enabled } : client
            ),
          }
          : null
      );
      message.success(t("common.success"));
    } catch {
      message.error(t("common.error"));
    }
  };

  const handleToggleFile = async (fileName: string, enabled: boolean) => {
    try {
      await agentApi.toggleFileEnabled(fileName, enabled);
      setConfig((prev) =>
        prev
          ? {
            ...prev,
            files: prev.files.map((file) =>
              file.name === fileName ? { ...file, enabled } : file
            ),
          }
          : null
      );
      message.success(t("common.success"));
    } catch {
      message.error(t("common.error"));
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!config) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
        <Text type="secondary">{t("common.noData")}</Text>
      </div>
    );
  }

  const tabItems = [
    {
      key: "basic",
      label: (
        <span>
          <SettingOutlined />
          {t("sidebar.config")}
        </span>
      ),
      children: (
        <Card size="small">
          <List size="small">
            <List.Item>
              <Text strong>{t("agent.name")}</Text>
              <Text>{config.name}</Text>
            </List.Item>
            <List.Item>
              <Text strong>{t("agent.model")}</Text>
              <Text>{config.model_id || "-"}</Text>
            </List.Item>
            <List.Item>
              <Text strong>{t("agent.temperature")}</Text>
              <Text>{config.temperature}</Text>
            </List.Item>
            <List.Item>
              <Text strong>{t("agent.maxTurns")}</Text>
              <Text>{config.max_turns}</Text>
            </List.Item>
            <List.Item>
              <Text strong>{t("agent.memory")}</Text>
              <Switch checked={config.enable_memory} disabled size="small" />
            </List.Item>
          </List>
        </Card>
      ),
    },
    {
      key: "tools",
      label: (
        <span>
          <ToolOutlined />
          {t("sidebar.tools")} ({config.tools?.length || 0})
        </span>
      ),
      children: (
        <Card size="small">
          <List
            size="small"
            dataSource={config.tools || []}
            renderItem={(tool) => (
              <List.Item
                actions={[
                  <Switch
                    key="toggle"
                    checked={tool.enabled}
                    onChange={(checked) => handleToggleTool(tool.name, checked)}
                    size="small"
                  />,
                ]}
              >
                <List.Item.Meta
                  title={tool.name}
                  description={tool.description || "-"}
                />
              </List.Item>
            )}
            locale={{ emptyText: t("common.noData") }}
          />
        </Card>
      ),
    },
    {
      key: "mcp",
      label: (
        <span>
          <ApiOutlined />
          MCP ({config.mcp_clients?.length || 0})
        </span>
      ),
      children: (
        <Card size="small">
          <List
            size="small"
            dataSource={config.mcp_clients || []}
            renderItem={(client) => (
              <List.Item
                actions={[
                  <Switch
                    key="toggle"
                    checked={client.enabled}
                    onChange={(checked) => handleToggleMCP(client.name, checked)}
                    size="small"
                  />,
                ]}
              >
                <List.Item.Meta
                  title={client.display_name || client.name}
                  description={client.transport}
                />
              </List.Item>
            )}
            locale={{ emptyText: t("common.noData") }}
          />
        </Card>
      ),
    },
    {
      key: "files",
      label: (
        <span>
          <FileTextOutlined />
          {t("sidebar.files")} ({config.files?.length || 0})
        </span>
      ),
      children: (
        <Card size="small">
          <List
            size="small"
            dataSource={config.files || []}
            renderItem={(file) => (
              <List.Item
                actions={[
                  <Switch
                    key="toggle"
                    checked={file.enabled !== false}
                    onChange={(checked) => handleToggleFile(file.name, checked)}
                    size="small"
                  />,
                ]}
              >
                <List.Item.Meta
                  title={file.name}
                  description={`${file.lines} ${t("agent.lines")}`}
                />
              </List.Item>
            )}
            locale={{ emptyText: t("common.noData") }}
          />
        </Card>
      ),
    },
  ];

  return (
    <div className="config-page">
      <div className="config-header">
        <Title level={4}>{t("chat.agentConfig")}</Title>
        <Text type="secondary">{config.workspace_dir}</Text>
      </div>
      <Tabs defaultActiveKey="basic" items={tabItems} className="config-tabs" />

      <style>{`
        .config-page {
          height: 100%;
          display: flex;
          flex-direction: column;
          padding: 16px;
          overflow: auto;
          background: ${isDark ? "#141414" : "#f5f5f5"};
        }
        .config-header {
          margin-bottom: 16px;
        }
        .config-tabs {
          flex: 1;
        }
        .config-tabs .ant-tabs-content {
          height: 100%;
        }
      `}</style>
    </div>
  );
}
