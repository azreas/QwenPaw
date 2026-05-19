import { useTranslation } from "react-i18next";
import { Layout, Menu } from "antd";
import {
  FileOutlined,
  ToolOutlined,
  ApiOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import { useTheme } from "../../contexts/ThemeContext";

const { Sider, Content } = Layout;

const CONFIG_PATH_TO_KEY: Record<string, string> = {
  "/config/workspace": "workspace",
  "/config/skills": "skills",
  "/config/tools": "tools",
  "/config/mcp": "mcp",
};

const KEY_TO_CONFIG_PATH: Record<string, string> = {
  workspace: "/config/workspace",
  skills: "/config/skills",
  tools: "/config/tools",
  mcp: "/config/mcp",
};

export default function ConfigLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { isDark } = useTheme();

  const selectedKey = CONFIG_PATH_TO_KEY[location.pathname] || "workspace";

  const handleMenuClick = ({ key }: { key: string }) => {
    const path = KEY_TO_CONFIG_PATH[key];
    if (path) {
      navigate(path);
    }
  };

  const menuItems = [
    { key: "workspace", icon: <FileOutlined />, label: t("config.workspace") },
    { key: "skills", icon: <ToolOutlined />, label: t("config.skills") },
    { key: "tools", icon: <SettingOutlined />, label: t("config.tools") },
    { key: "mcp", icon: <ApiOutlined />, label: t("config.mcp") },
  ];

  return (
    <Layout style={{ height: "100%", background: "transparent" }}>
      <Sider
        width={180}
        style={{
          background: isDark ? "#1f1f1f" : "#fff",
          borderRight: `1px solid ${isDark ? "#303030" : "#f0f0f0"}`,
        }}
      >
        <div
          style={{
            padding: "16px",
            fontSize: "14px",
            fontWeight: 600,
            borderBottom: `1px solid ${isDark ? "#303030" : "#f0f0f0"}`,
            color: isDark ? "#fff" : "#333",
          }}
        >
          {t("chat.agentConfig")}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={handleMenuClick}
          items={menuItems}
          style={{
            borderRight: "none",
            background: "transparent",
          }}
          theme={isDark ? "dark" : "light"}
        />
      </Sider>
      <Content style={{ padding: "16px", overflow: "auto" }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
