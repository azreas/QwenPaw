import React, { useState } from "react"
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Button,
  theme,
  Space,
  Typography,
  Tag,
} from "antd"
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  DashboardOutlined,
  ApiOutlined,
  TeamOutlined,
  UserSwitchOutlined,
  SafetyOutlined,
  FileTextOutlined,
  AlertOutlined,
  BarChartOutlined,
  DatabaseOutlined,
  SettingOutlined,
} from "@ant-design/icons"
import { Outlet, useNavigate, useLocation } from "react-router-dom"
import { useAuth } from "@/features/auth/useAuth"
import {
  resolveNavKey,
  getVisibleNavItems,
  navGroups,
} from "@/navigation/enterpriseNavigation"
import "./EnterpriseShell.css"

const { Header, Sider, Content } = Layout
const { Text } = Typography

// 图标映射
const iconMap: Record<string, React.ReactNode> = {
  dashboard: <DashboardOutlined />,
  tenants: <TeamOutlined />,
  users: <UserSwitchOutlined />,
  abilities: <ApiOutlined />,
  policies: <SafetyOutlined />,
  audit: <FileTextOutlined />,
  evaluation: <BarChartOutlined />,
  badCases: <AlertOutlined />,
  metrics: <BarChartOutlined />,
  quota: <DatabaseOutlined />,
  security: <SafetyOutlined />,
  settings: <SettingOutlined />,
}

const EnterpriseShell: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const {
    token: { colorBgContainer },
  } = theme.useToken()

  const selectedKey = resolveNavKey(location.pathname)
  const visibleNavItems = getVisibleNavItems(user?.role, user?.authDisabled)

  const handleMenuClick = (key: string) => {
    const item = visibleNavItems.find((i) => i.key === key)
    if (item) {
      navigate(item.path)
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate("/login", { replace: true })
  }

  // 构建菜单项 - 按分组
  const menuItems = Object.entries(navGroups).flatMap(([groupKey, groupLabel]) => {
    const groupItems = visibleNavItems
      .filter((item) => item.group === groupKey)
      .map((item) => ({
      key: item.key,
      icon: iconMap[item.key],
      label: item.badge ? (
        <Space size={6}>
          <span>{item.label}</span>
          {!collapsed && <Tag color="default">{item.badge}</Tag>}
        </Space>
      ) : (
        item.label
      ),
    }))

    if (groupItems.length === 0) return []

    return [
      {
        type: "group" as const,
        key: `group-${groupKey}`,
        label: groupLabel,
        children: groupItems,
      },
    ]
  })

  const userMenuItems = user?.authDisabled
    ? []
    : [
        {
          key: "logout",
          icon: <LogoutOutlined />,
          label: "退出登录",
          onClick: handleLogout,
        },
      ]

  return (
    <Layout className="enterprise-shell">
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        className="enterprise-shell-sider"
        width={240}
        collapsedWidth={64}
      >
        <div className="enterprise-shell-logo">
          {collapsed ? (
            <span className="logo-collapsed">Q</span>
          ) : (
            <Space>
              <span className="logo-icon">Q</span>
              <span className="logo-text">企业工作台</span>
            </Space>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selectedKey ? [selectedKey] : []}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
          className="enterprise-shell-menu"
        />
      </Sider>
      <Layout className="enterprise-shell-main">
        <Header
          style={{
            padding: "0 24px",
            background: colorBgContainer,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: "16px", width: 64, height: 64 }}
          />

          <Dropdown
            menu={{ items: userMenuItems }}
            placement="bottomRight"
            trigger={["click"]}
          >
            <Space
              style={{ cursor: "pointer" }}
              className="enterprise-shell-user-dropdown"
            >
              <Avatar size="small" icon={<UserOutlined />} />
              <Text>{user?.username || "用户"}</Text>
            </Space>
          </Dropdown>
        </Header>
        <Content
          className="enterprise-shell-content"
          style={{
            margin: "24px",
            minHeight: "calc(100vh - 112px)",
            background: colorBgContainer,
            borderRadius: 8,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default EnterpriseShell
