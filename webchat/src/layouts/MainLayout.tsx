import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Layout, Menu, Button, Dropdown } from "antd";
import type { MenuProps } from "antd";
import {
  SparkChatTabFill,
  SparkLocalFileLine,
  SparkMagicWandLine,
  SparkToolLine,
  SparkMcpMcpLine,
  SparkModifyLine,
  SparkTaskLine,
  SparkMessageLine,
  SparkBarChartLine,
  SparkMenuFoldLine,
  SparkMenuExpandLine,
} from "@agentscope-ai/icons";
import { LogoutOutlined, SunOutlined, MoonOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import { useUser } from "../contexts/UserContext";
import { useTheme } from "../contexts/ThemeContext";
import { useCapabilities } from "../contexts/CapabilityContext";
import { KEY_TO_PATH, PATH_TO_KEY } from "../constants/navigation";
import { webchatPath } from "../utils/deployment";

const { Sider, Content } = Layout;
type MenuItem = Required<MenuProps>["items"][number];

export default function MainLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useUser();
  const { isDark, toggleTheme } = useTheme();
  const { data: capabilityData, loading: capabilityLoading } = useCapabilities();
  const [collapsed, setCollapsed] = useState(false);
  const capabilities = capabilityData?.capabilities;
  const hasLoadedCapabilities = !capabilityLoading && Boolean(capabilities);

  // Determine selected key from current path
  const selectedKey = PATH_TO_KEY[location.pathname] || "chat";

  const handleMenuClick = ({ key }: { key: string }) => {
    const path = KEY_TO_PATH[key];
    if (path) {
      navigate(path);
    }
  };

  const canShow = (key: keyof NonNullable<typeof capabilities>) => {
    if (!hasLoadedCapabilities || !capabilities) return false;
    return capabilities[key] === true;
  };

  const workspaceItems: MenuItem[] = [
    canShow("files")
      ? { key: "files", icon: <SparkLocalFileLine size={16} />, label: t("config.files") }
      : null,
    canShow("skills")
      ? { key: "skills", icon: <SparkMagicWandLine size={16} />, label: t("config.skills") }
      : null,
    canShow("tools")
      ? { key: "tools", icon: <SparkToolLine size={16} />, label: t("config.tools") }
      : null,
    canShow("mcp")
      ? { key: "mcp", icon: <SparkMcpMcpLine size={16} />, label: t("config.mcp") }
      : null,
    canShow("advanced_config")
      ? { key: "agentConfig", icon: <SparkModifyLine size={16} />, label: t("agentConfig.title") }
      : null,
  ].filter(Boolean) as MenuItem[];

  const myItems: MenuItem[] = [
    canShow("tasks")
      ? { key: "tasks", icon: <SparkTaskLine size={16} />, label: t("nav.tasks") }
      : null,
    { key: "messages", icon: <SparkMessageLine size={16} />, label: t("nav.messages") },
    { key: "shortcuts", icon: <ThunderboltOutlined />, label: t("nav.shortcuts") },
  ].filter(Boolean) as MenuItem[];

  const systemItems: MenuItem[] = [
    canShow("usage")
      ? { key: "tokenUsage", icon: <SparkBarChartLine size={16} />, label: t("nav.tokenUsage") }
      : null,
  ].filter(Boolean) as MenuItem[];

  const menuItems: MenuItem[] = [
    { key: "chat", icon: <SparkChatTabFill size={16} />, label: t("chat.chat") },
    ...(workspaceItems.length > 0
      ? [
          { type: "divider" as const },
          { type: "group" as const, label: t("config.workspace"), key: "workspace-group" },
          ...workspaceItems,
        ]
      : []),
    { type: "divider" as const },
    { type: "group" as const, label: t("nav.my"), key: "my-group" },
    ...myItems,
    ...(systemItems.length > 0
      ? [
          { type: "divider" as const },
          { type: "group" as const, label: t("nav.system"), key: "system-group" },
          ...systemItems,
        ]
      : []),
  ];

  return (
    <Layout className="chat-layout">
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={200}
        collapsedWidth={60}
        className="chat-sider"
        trigger={null}
      >
        <div className="sider-header">
          {!collapsed && <span className="sider-title">小轩</span>}
          <Button
            type="text"
            icon={collapsed ? <SparkMenuExpandLine size={20} /> : <SparkMenuFoldLine size={20} />}
            onClick={() => setCollapsed(!collapsed)}
            className="collapse-btn"
          />
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={handleMenuClick}
          items={menuItems}
          className="sider-menu"
          inlineCollapsed={collapsed}
        />
        <div className="sider-footer">
          <div className="sider-footer-actions">
            <Button
              type="text"
              icon={isDark ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              className="theme-toggle-btn"
              title={isDark ? t("theme.light") : t("theme.dark")}
            />
            <Dropdown
              menu={{
                items: [
                  {
                    key: "logout",
                    label: t("common.logout"),
                    icon: <LogoutOutlined />,
                    danger: true,
                    onClick: () => {
                      logout();
                      navigate(webchatPath("/login"), { replace: true });
                    },
                  },
                ],
              }}
              placement="topLeft"
            >
              <Button type="text" className="user-btn">
                {collapsed ? user?.username?.[0]?.toUpperCase() || "U" : user?.username || "User"}
              </Button>
            </Dropdown>
          </div>
        </div>

        <style>{`
          .sider-footer-actions {
            display: flex;
            align-items: center;
            gap: 4px;
          }
          .theme-toggle-btn {
            color: ${isDark ? "#fff" : "#333"};
            padding: 4px 8px;
          }
          .theme-toggle-btn:hover {
            background: ${isDark ? "#303030" : "#f5f5f5"};
          }
        `}</style>
      </Sider>
      <Content className="chat-content">
        <Outlet />
      </Content>

      <style>{`
        .chat-layout {
          height: 100vh;
          background: ${isDark ? "#141414" : "#f5f5f5"};
        }
        .chat-sider {
          background: ${isDark ? "#1f1f1f" : "#fff"} !important;
          display: flex !important;
          flex-direction: column !important;
          position: relative !important;
        }
        .chat-sider .ant-layout-sider-children {
          display: flex !important;
          flex-direction: column !important;
          height: 100% !important;
        }
        .sider-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px;
          border-bottom: 1px solid ${isDark ? "#303030" : "#f0f0f0"};
          flex-shrink: 0;
        }
        .sider-title {
          font-size: 16px;
          font-weight: 600;
        }
        .collapse-btn {
          color: ${isDark ? "#fff" : "#333"};
        }
        .sider-menu {
          border-right: none !important;
          flex: 1 1 auto !important;
          overflow-y: auto !important;
          min-height: 0 !important;
        }
        .sider-footer {
          flex-shrink: 0;
          padding: 12px;
          border-top: 1px solid ${isDark ? "#303030" : "#f0f0f0"};
          background: ${isDark ? "#1f1f1f" : "#fff"};
          position: sticky;
          bottom: 0;
          z-index: 1;
        }
        .user-btn {
          flex: 1;
          text-align: left;
          color: ${isDark ? "#fff" : "#333"};
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .user-btn:hover {
          background: ${isDark ? "#303030" : "#f5f5f5"};
        }
        .chat-content {
          display: flex;
          flex-direction: column;
          background: ${isDark ? "#141414" : "#f5f5f5"};
          overflow: hidden;
        }
      `}</style>
    </Layout>
  );
}
