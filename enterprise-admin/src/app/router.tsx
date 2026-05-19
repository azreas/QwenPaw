import React from "react"
import {
  createBrowserRouter,
  Navigate,
  Outlet,
  useNavigate,
} from "react-router-dom"
import { Spin, message } from "antd"
import { useAuth } from "@/features/auth/useAuth"
import { canAccessNavItem, enterpriseNavItems } from "@/navigation/enterpriseNavigation"
import LoginPage from "@/pages/LoginPage"
import DashboardPage from "@/pages/DashboardPage"
import TenantsPage from "@/pages/TenantsPage"
import EntryConfigPage from "@/pages/EntryConfigPage"
import UsersPage from "@/pages/UsersPage"
import AbilitiesPage from "@/pages/AbilitiesPage"
import ModelsPage from "@/pages/ModelsPage"
import BusinessTracePage from "@/pages/BusinessTracePage"
import BadCasesPage from "@/pages/BadCasesPage"
import EvaluationPage from "@/pages/EvaluationPage"
import QuotaPage from "@/pages/QuotaPage"
import SecurityPage from "@/pages/SecurityPage"
import BackupsPage from "@/pages/BackupsPage"
import DiagnosticsPage from "@/pages/DiagnosticsPage"
import MetricsPage from "@/pages/MetricsPage"
import SettingsPage from "@/pages/SettingsPage"
import ModuleLandingPage from "@/pages/ModuleLandingPage"
import PoliciesPage from "@/pages/PoliciesPage"
import EnterpriseShell from "@/layouts/EnterpriseShell"

/**
 * 认证守卫组件
 * 检查用户是否已认证，未认证则重定向到登录页
 */
const AuthGuard: React.FC = () => {
  const { isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()

  React.useEffect(() => {
    if (!loading && !isAuthenticated) {
      message.warning("请先登录")
      navigate("/login", { state: { redirect: window.location.pathname } })
    }
  }, [isAuthenticated, loading, navigate])

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return <Outlet />
}

/**
 * 已登录用户访问登录页时的守卫
 * 如果用户已登录，重定向到首页
 */
const LoginGuard: React.FC = () => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

interface RoleGuardProps {
  navKey: string
  children: React.ReactElement
}

const RoleGuard: React.FC<RoleGuardProps> = ({ navKey, children }) => {
  const { user } = useAuth()
  const item = enterpriseNavItems.find((item) => item.key === navKey)

  if (item && !canAccessNavItem(item, user?.role, user?.authDisabled)) {
    return (
      <ModuleLandingPage
        title="无权访问"
        status="403"
        description="当前角色无权访问该模块，请联系平台管理员调整角色或租户绑定。"
      />
    )
  }

  return children
}

// 声明 VITE_ROUTER_BASENAME: string

// 路由配置
export const router = createBrowserRouter(
  [
    {
      element: <LoginGuard />,
      children: [
        {
          path: "/login",
          element: <LoginPage />,
        },
      ],
    },
    {
      element: <AuthGuard />,
      children: [
        {
          element: <EnterpriseShell />,
          children: [
            {
              path: "/",
              element: <Navigate to="/dashboard" replace />,
            },
            {
              path: "/dashboard",
              element: <DashboardPage />,
            },
            {
              path: "/tenants",
              element: <TenantsPage />,
            },
            {
              path: "/entry-config",
              element: (
                <RoleGuard navKey="entryConfig">
                  <EntryConfigPage />
                </RoleGuard>
              ),
            },
            {
              path: "/users",
              element: <UsersPage />,
            },
            {
              path: "/abilities",
              element: <AbilitiesPage />,
            },
            {
              path: "/models",
              element: (
                <RoleGuard navKey="models">
                  <ModelsPage />
                </RoleGuard>
              ),
            },
            {
              path: "/policies",
              element: (
                <RoleGuard navKey="policies">
                  <PoliciesPage />
                </RoleGuard>
              ),
            },
            {
              path: "/audit",
              element: <BusinessTracePage />,
            },
            {
              path: "/evaluation",
              element: <EvaluationPage />,
            },
            {
              path: "/bad-cases",
              element: <BadCasesPage />,
            },
            {
              path: "/metrics",
              element: (
                <RoleGuard navKey="metrics">
                  <MetricsPage />
                </RoleGuard>
              ),
            },
            {
              path: "/quota",
              element: (
                <RoleGuard navKey="quota">
                  <QuotaPage />
                </RoleGuard>
              ),
            },
            {
              path: "/security",
              element: (
                <RoleGuard navKey="security">
                  <SecurityPage />
                </RoleGuard>
              ),
            },
            {
              path: "/backups",
              element: (
                <RoleGuard navKey="backups">
                  <BackupsPage />
                </RoleGuard>
              ),
            },
            {
              path: "/diagnostics",
              element: (
                <RoleGuard navKey="diagnostics">
                  <DiagnosticsPage />
                </RoleGuard>
              ),
            },
            {
              path: "/settings",
              element: (
                <RoleGuard navKey="settings">
                  <SettingsPage />
                </RoleGuard>
              ),
            },
          ],
        },
      ],
    },
    {
      path: "*",
      element: (
        <ModuleLandingPage
          title="页面不存在"
          description="您访问的页面不存在，请检查地址是否正确"
          status="404"
        />
      ),
    },
  ],
  {
    basename: import.meta.env.VITE_ROUTER_BASENAME ?? "/enterprise-admin",
  },
)

export default router
