import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Drawer, List, Spin, message, Empty, Tooltip, Dropdown } from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  HistoryOutlined,
  CheckOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import { SparkDownLine } from "@agentscope-ai/icons";
import { useTheme } from "../../../../contexts/ThemeContext";
import { apiRequest } from "../../../../api/config";
import { providerApi, type ProviderInfo, type ActiveModelsInfo } from "../../../../api/modules/provider";
import { webchatPath } from "../../../../utils/deployment";

interface ChatSession {
  id: string;
  session_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

const providerIcons: Record<string, string> = {
  openai: "https://cdn.oaistatic.com/assets/apple-touch-icon-mz9nytnj.webp",
  qwen: "https://img.alicdn.com/imgextra/i3/O1CN01PlT3oG1WkUzZbK5Yn_!!6000000002826-2-tps-512-512.png",
  deepseek: "https://cdn.deepseek.com/logo.png",
  moonshot: "https://img.alicdn.com/imgextra/i4/O1CN01pHeZxr1h9aMfU1XhE_!!6000000004236-2-tps-512-512.png",
  default: "https://gw.alicdn.com/imgextra/i2/O1CN01pyXzjQ1EL1PuZMlSd_!!6000000000334-2-tps-288-288.png",
};

function getProviderIcon(providerId: string): string {
  return providerIcons[providerId] || providerIcons.default;
}

export default function ChatPage() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [activeModels, setActiveModels] = useState<ActiveModelsInfo | null>(null);
  const [modelLoading, setModelLoading] = useState(false);
  const [modelSaving, setModelSaving] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      // 首先获取当前用户的agent信息
      const userResponse = await apiRequest<{ agent_id: string; user_id: string; username: string }>("/webchat/me");
      const agentId = userResponse.agent_id;
      
      // 然后使用agent_id过滤聊天记录
      const response = await apiRequest<{ sessions: ChatSession[] }>(`/webchat/sessions?agent_id=${encodeURIComponent(agentId)}`);
      setSessions(response.sessions || []);
    } catch (error) {
      console.error("Failed to load sessions:", error);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const loadModels = useCallback(async () => {
    setModelLoading(true);
    try {
      const [provData, activeData] = await Promise.all([
        providerApi.listProviders(),
        providerApi.getActiveModels(),
      ]);
      if (Array.isArray(provData)) {
        const eligible = provData.filter(
          (p) => (p.models?.length ?? 0) + (p.extra_models?.length ?? 0) > 0
        );
        setProviders(eligible);
      }
      if (activeData) setActiveModels(activeData);
    } catch (error) {
      console.error("Failed to load models:", error);
    } finally {
      setModelLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
    loadModels();
  }, [loadSessions, loadModels]);

  useEffect(() => {
    if (sessionId) {
      setActiveSessionId(sessionId);
    }
  }, [sessionId]);

  const handleNewSession = async () => {
    try {
      const response = await apiRequest<{ session_id: string }>("/webchat/sessions", {
        method: "POST",
        body: JSON.stringify({}),
      });
      if (response.session_id) {
        await loadSessions();
        // 导航到新会话，这将自动更新ChatArea组件
        navigate(webchatPath(`/chat/${response.session_id}`));
      }
    } catch (error) {
      console.error("Failed to create session:", error);
      message.error(t("common.error"));
    }
  };

  const handleSelectSession = (sessionId: string, _sessionInternalId: string) => {
    // 导航到选定的会话，这将自动更新ChatArea组件
    navigate(webchatPath(`/chat/${sessionId}`));
    setHistoryOpen(false);
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiRequest(`/webchat/sessions/${sessionId}`, { method: "DELETE" });
      // 重新加载会话列表
      await loadSessions();
      // 如果删除的是当前活跃的会话，则导航回主聊天页面
      if (activeSessionId === sessionId) {
        navigate(webchatPath("/chat"));
      }
      message.success(t("common.success"));
    } catch (error) {
      console.error("Failed to delete session:", error);
      message.error(t("common.error"));
    }
  };

  const handleSelectModel = async (providerId: string, modelId: string) => {
    if (modelSaving) return;
    const currentProvider = activeModels?.active_llm?.provider_id;
    const currentModel = activeModels?.active_llm?.model;
    if (providerId === currentProvider && modelId === currentModel) {
      setModelOpen(false);
      return;
    }
    setModelSaving(true);
    setModelOpen(false);
    try {
      await providerApi.setActiveLlm({
        provider_id: providerId,
        model: modelId,
      });
      setActiveModels({
        active_llm: { provider_id: providerId, model: modelId },
      });
      message.success(t("common.success"));
    } catch (error) {
      console.error("Failed to set model:", error);
      message.error(t("common.error"));
    } finally {
      setModelSaving(false);
    }
  };

  const currentSession = sessions.find((s) => s.id === activeSessionId);
  const chatName = currentSession?.name || t("chat.newChat");

  const activeProviderId = activeModels?.active_llm?.provider_id;
  const activeModelId = activeModels?.active_llm?.model;

  const activeModelName = useMemo(() => {
    if (!activeProviderId || !activeModelId) return t("modelSelector.selectModel");
    for (const p of providers) {
      if (p.id === activeProviderId) {
        const allModels = [...(p.models ?? []), ...(p.extra_models ?? [])];
        const m = allModels.find((m) => m.id === activeModelId);
        if (m) return m.name || m.id;
      }
    }
    return activeModelId;
  }, [activeProviderId, activeModelId, providers, t]);

  const modelMenuItems = useMemo(() => {
    if (modelLoading || providers.length === 0) return [];
    
    return providers.map((provider) => {
      const isProviderActive = provider.id === activeProviderId;
      const allModels = [...(provider.models ?? []), ...(provider.extra_models ?? [])];
      return {
        key: provider.id,
        label: (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <img
              src={getProviderIcon(provider.id)}
              alt=""
              style={{ width: 20, height: 20, borderRadius: 4 }}
            />
            <span style={{ flex: 1 }}>{provider.name}</span>
            {isProviderActive && <CheckOutlined style={{ color: "#1890ff" }} />}
          </div>
        ),
        style: {
          background: isProviderActive ? (isDark ? "#177ddc20" : "#e6f7ff") : "transparent",
        },
        children: allModels.map((model) => {
          const isActive = isProviderActive && model.id === activeModelId;
          return {
            key: model.id,
            label: (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>{model.name || model.id}</span>
                {isActive && <CheckOutlined style={{ color: "#1890ff" }} />}
              </div>
            ),
            onClick: () => handleSelectModel(provider.id, model.id),
            style: {
              background: isActive ? (isDark ? "#177ddc20" : "#e6f7ff") : "transparent",
            },
          };
        }),
      };
    });
  }, [providers, modelLoading, activeProviderId, activeModelId, isDark, t]);

  return (
    <div className="chat-page">
      <div className="chat-header">
        <span className="chat-title">{chatName}</span>
        <div className="chat-actions">
          <Dropdown
            open={modelOpen}
            onOpenChange={setModelOpen}
            menu={{
              items: modelMenuItems.length > 0 ? modelMenuItems : [
                {
                  key: "loading",
                  label: modelLoading ? (
                    <div style={{ padding: "8px 12px", textAlign: "center" }}>
                      <Spin size="small" />
                    </div>
                  ) : (
                    <div style={{ padding: "8px 12px", textAlign: "center", color: isDark ? "#666" : "#999" }}>
                      {t("modelSelector.noConfiguredModels")}
                    </div>
                  ),
                  disabled: true,
                },
              ],
            }}
            trigger={["click"]}
            placement="bottomLeft"
          >
            <Tooltip title={t("chat.modelSelectTooltip")} mouseEnterDelay={0.5}>
              <div className="model-selector">
                {modelSaving && <LoadingOutlined style={{ fontSize: 11, color: "#FF7F16" }} />}
                {activeProviderId && (
                  <img
                    src={getProviderIcon(activeProviderId)}
                    alt=""
                    style={{ width: 16, height: 16, borderRadius: 4 }}
                  />
                )}
                <span className="model-name">{activeModelName}</span>
                <SparkDownLine style={{ fontSize: 10 }} />
              </div>
            </Tooltip>
          </Dropdown>
          <Tooltip title={t("chat.newChatTooltip")} mouseEnterDelay={0.5}>
            <Button
              type="text"
              icon={<PlusOutlined />}
              onClick={handleNewSession}
            />
          </Tooltip>
          <Tooltip title={t("chat.chatHistoryTooltip")} mouseEnterDelay={0.5}>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => setHistoryOpen(true)}
            />
          </Tooltip>
        </div>
      </div>
      <div className="chat-body">
        {/* ChatArea component not available */}
      </div>

      <Drawer
        title={t("chat.history")}
        placement="right"
        width={320}
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        className={isDark ? "dark-drawer" : ""}
      >
        <Spin spinning={sessionsLoading}>
          {sessions.length === 0 ? (
            <Empty description={t("common.noData")} />
          ) : (
            <List
              size="small"
              dataSource={sessions}
              renderItem={(session) => (
                <List.Item
                  className={`session-item ${activeSessionId === session.id ? "active" : ""}`}
                  onClick={() => handleSelectSession(session.id, session.session_id)}
                  style={{
                    cursor: "pointer",
                    borderRadius: 6,
                    marginBottom: 4,
                    background: activeSessionId === session.id
                      ? (isDark ? "#177ddc" : "#e6f7ff")
                      : "transparent",
                  }}
                  actions={[
                    <Button
                      key="delete"
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      danger
                      onClick={(e) => handleDeleteSession(session.id, e)}
                    />,
                  ]}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {session.name || t("chat.newChat")}
                  </span>
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Drawer>

      <style>{`
        .chat-page {
          height: 100%;
          display: flex;
          flex-direction: column;
          background: ${isDark ? "#141414" : "#f5f5f5"};
        }
        .chat-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          background: ${isDark ? "#1f1f1f" : "#fff"};
          border-bottom: 1px solid ${isDark ? "#303030" : "#f0f0f0"};
          flex-shrink: 0;
        }
        .chat-title {
          font-size: 14px;
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 200px;
        }
        .chat-actions {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .model-selector {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 8px;
          border-radius: 6px;
          cursor: pointer;
          background: ${isDark ? "#303030" : "#f5f5f5"};
        }
        .model-selector:hover {
          background: ${isDark ? "#404040" : "#e8e8e8"};
        }
        .model-name {
          font-size: 13px;
          max-width: 120px;
          overflow: hidden;
          text-overflow: ellipsis;
          whiteSpace: nowrap;
        }
        .chat-body {
          flex: 1;
          overflow: hidden;
        }
        .session-item:hover {
          background-color: ${isDark ? "#303030" : "#f5f5f5"} !important;
        }
        .provider-item:hover {
          background-color: ${isDark ? "#303030" : "#f5f5f5"} !important;
        }
        .provider-item:hover .model-submenu {
          display: block !important;
        }
        .model-item:hover {
          background-color: ${isDark ? "#404040" : "#e8e8e8"} !important;
        }
      `}</style>
    </div>
  );
}
