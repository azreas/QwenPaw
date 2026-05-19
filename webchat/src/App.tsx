import { createGlobalStyle } from "antd-style";
import { ConfigProvider, App as AntdApp } from "antd";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import type { Locale } from "antd/es/locale";
import { theme as antdTheme } from "antd";
import { ThemeProvider, useTheme } from "./contexts/ThemeContext";
import { UserProvider } from "./contexts/UserContext";
import { CapabilityProvider, useCapabilities } from "./contexts/CapabilityContext";
import type { MemberCapabilities } from "./api/types/capabilities";
import LoginPage from "./pages/Login";
import ChatPage from "./pages/Chat";
import FilesConfig from "./pages/Config/Files";
import MainLayout from "./layouts/MainLayout";
import SkillsConfig from "./pages/Config/Skills";
import ToolsConfig from "./pages/Config/Tools";
import MCPConfig from "./pages/Config/MCP";
import AgentConfigPage from "./pages/Config/AgentConfig";
import TasksPage from "./pages/My/Tasks";
import MessagesPage from "./pages/My/Messages";
import ShortcutsPage from "./pages/My/Shortcuts";
import TokenUsagePage from "./pages/System/TokenUsage";
import { authApi } from "./api/modules/auth";
import { getApiToken, clearAuthToken } from "./api/config";
import {
  routerBasename,
  stripRouterBasename,
  webchatPath,
  webchatRoutePrefix,
} from "./utils/deployment";
import "./styles/global.css";

const antdLocaleMap: Record<string, Locale> = {
  zh: zhCN,
  en: enUS,
};

const GlobalStyle = createGlobalStyle`
* {
  margin: 0;
  box-sizing: border-box;
}
`;

function AuthGuard({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<"loading" | "auth-required" | "ok">(
    "loading"
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await authApi.status();
        if (cancelled) return;

        if (!res.has_users) {
          setStatus("auth-required");
          return;
        }

        const token = getApiToken();
        if (!token) {
          setStatus("auth-required");
          return;
        }

        try {
          const r = await authApi.verify();
          if (cancelled) return;
          if (r.valid) {
            setStatus("ok");
          } else {
            clearAuthToken();
            setStatus("auth-required");
          }
        } catch (e) {
          console.error("Verify token error:", e);
          if (!cancelled) {
            clearAuthToken();
            setStatus("auth-required");
          }
        }
      } catch (e) {
        console.error("Failed to check auth status:", e);
        if (!cancelled) setStatus("auth-required");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "loading") {
    return (
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh"
      }}>
        <span>Loading...</span>
      </div>
    );
  }

  if (status === "auth-required") {
    const redirectPath = stripRouterBasename(window.location.pathname);
    return (
      <Navigate
        to={`${webchatPath("/login")}?redirect=${encodeURIComponent(redirectPath)}`}
        replace
      />
    );
  }

  return <>{children}</>;
}

function CapabilityRouteGuard({
  capability,
  children,
}: {
  capability: keyof MemberCapabilities;
  children: React.ReactNode;
}) {
  const { data, loading } = useCapabilities();

  if (loading) {
    return (
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100%"
      }}>
        <span>Loading...</span>
      </div>
    );
  }

  if (data?.capabilities[capability] !== true) {
    return <Navigate to={webchatPath("/chat")} replace />;
  }

  return <>{children}</>;
}

function AppInner() {
  const { i18n } = useTranslation();
  const { isDark } = useTheme();
  const lang = i18n.resolvedLanguage || i18n.language || "en";
  const [antdLocale] = useState<Locale>(antdLocaleMap[lang] ?? enUS);

  return (
    <BrowserRouter basename={routerBasename || undefined}>
      <GlobalStyle />
      <ConfigProvider
        locale={antdLocale}
        theme={{
          algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
          token: {
            colorPrimary: "#FF7F16",
          },
        }}
      >
        <AntdApp>
          <Routes>
            <Route path={`${webchatRoutePrefix}/login`} element={<LoginPage />} />
            <Route
              path={`${webchatRoutePrefix}/*`}
              element={
                <AuthGuard>
                  <CapabilityProvider>
                    <MainLayout />
                  </CapabilityProvider>
                </AuthGuard>
              }
            >
              <Route index element={<Navigate to={webchatPath("/chat")} replace />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="chat/:sessionId" element={<ChatPage />} />
              <Route
                path="config/files"
                element={<CapabilityRouteGuard capability="files"><FilesConfig /></CapabilityRouteGuard>}
              />
              <Route
                path="config/skills"
                element={<CapabilityRouteGuard capability="skills"><SkillsConfig /></CapabilityRouteGuard>}
              />
              <Route
                path="config/tools"
                element={<CapabilityRouteGuard capability="tools"><ToolsConfig /></CapabilityRouteGuard>}
              />
              <Route
                path="config/mcp"
                element={<CapabilityRouteGuard capability="mcp"><MCPConfig /></CapabilityRouteGuard>}
              />
              <Route
                path="config/agent-config"
                element={<CapabilityRouteGuard capability="advanced_config"><AgentConfigPage /></CapabilityRouteGuard>}
              />
              <Route
                path="my/tasks"
                element={<CapabilityRouteGuard capability="tasks"><TasksPage /></CapabilityRouteGuard>}
              />
              <Route path="my/messages" element={<MessagesPage />} />
              <Route path="my/shortcuts" element={<ShortcutsPage />} />
              <Route
                path="system/token-usage"
                element={<CapabilityRouteGuard capability="usage"><TokenUsagePage /></CapabilityRouteGuard>}
              />
            </Route>
          </Routes>
        </AntdApp>
      </ConfigProvider>
    </BrowserRouter>
  );
}

function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <AppInner />
      </UserProvider>
    </ThemeProvider>
  );
}

export default App;
