import { Suspense } from "react";
import { Layout, Spin } from "antd";
import { Routes, Route, useLocation, Navigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Sidebar from "../Sidebar";
import Header from "../Header";
import ConsolePollService from "../../components/ConsolePollService";
import { ChunkErrorBoundary } from "../../components/ChunkErrorBoundary";
import { lazyImportWithRetry } from "../../utils/lazyWithRetry";
import { resolveStaticSelectedKey } from "../navigationModel";
import { usePlugins } from "../../plugins/PluginContext";
import styles from "../index.module.less";

// Chat is eagerly loaded (default landing page)
import Chat from "../../pages/Chat";

// All other pages are lazily loaded with automatic retry on chunk failure
const ChannelsPage = lazyImportWithRetry("../../pages/Control/Channels");
const SessionsPage = lazyImportWithRetry("../../pages/Control/Sessions");
const InboxPage = lazyImportWithRetry("../../pages/Inbox");
const CronJobsPage = lazyImportWithRetry("../../pages/Control/CronJobs");
const HeartbeatPage = lazyImportWithRetry("../../pages/Control/Heartbeat");
const WecomTenantsPage = lazyImportWithRetry(
  "../../pages/Control/WecomTenants",
);
const WecomTenantMonitoringPage = lazyImportWithRetry(
  "../../pages/Control/WecomTenantMonitoring",
);
const WecomTenantMonitoringDetailPage = lazyImportWithRetry(
  "../../pages/Control/WecomTenantMonitoring/DetailPage",
);
const PlatformOverviewPage = lazyImportWithRetry(
  "../../pages/Platform/Overview",
);
const PlatformPoliciesPage = lazyImportWithRetry(
  "../../pages/Platform/Policies",
);
const PlatformUsersPage = lazyImportWithRetry("../../pages/Platform/Users");
const AgentConfigPage = lazyImportWithRetry("../../pages/Agent/Config");
const SkillsPage = lazyImportWithRetry("../../pages/Agent/Skills");
const SkillPoolPage = lazyImportWithRetry("../../pages/Settings/SkillPool");
const ToolsPage = lazyImportWithRetry("../../pages/Agent/Tools");
const WorkspacePage = lazyImportWithRetry("../../pages/Agent/Workspace");
const MCPPage = lazyImportWithRetry("../../pages/Agent/MCP");
const ACPPage = lazyImportWithRetry("../../pages/Agent/ACP");
const ModelsPage = lazyImportWithRetry("../../pages/Settings/Models");
const EnvironmentsPage = lazyImportWithRetry(
  "../../pages/Settings/Environments",
);
const SecurityPage = lazyImportWithRetry("../../pages/Settings/Security");
const TokenUsagePage = lazyImportWithRetry("../../pages/Settings/TokenUsage");
const AgentStatsPage = lazyImportWithRetry("../../pages/Settings/AgentStats");
const VoiceTranscriptionPage = lazyImportWithRetry(
  "../../pages/Settings/VoiceTranscription",
);
const AgentsPage = lazyImportWithRetry("../../pages/Settings/Agents");
const DebugPage = lazyImportWithRetry("../../pages/Settings/Debug");
const BackupsPage = lazyImportWithRetry("../../pages/Settings/Backups");
const PluginManagerPage = lazyImportWithRetry(
  "../../pages/Settings/PluginManager",
);

const { Content } = Layout;

export default function MainLayout() {
  const { t } = useTranslation();
  const location = useLocation();
  const currentPath = location.pathname;
  const { pluginRoutes } = usePlugins();

  // Resolve selected key: check static routes first, then plugin routes
  let selectedKey = resolveStaticSelectedKey(currentPath);
  if (!selectedKey) {
    const matchedPlugin = pluginRoutes.find(
      (route) => currentPath === route.path,
    );
    selectedKey = matchedPlugin
      ? matchedPlugin.path.replace(/^\//, "")
      : "chat";
  }

  return (
    <Layout className={styles.mainLayout}>
      <Header />
      <Layout>
        <Sidebar selectedKey={selectedKey} />
        <Content className="page-container">
          <ConsolePollService />
          <div className="page-content">
            <ChunkErrorBoundary resetKey={currentPath}>
              <Suspense
                fallback={
                  <Spin
                    tip={t("common.loading")}
                    style={{ display: "block", margin: "20vh auto" }}
                  />
                }
              >
                <Routes>
                  <Route path="/" element={<Navigate to="/chat" replace />} />
                  <Route path="/chat/*" element={<Chat />} />
                  <Route path="/channels" element={<ChannelsPage />} />
                  <Route path="/sessions" element={<SessionsPage />} />
                  <Route path="/inbox" element={<InboxPage />} />
                  <Route path="/cron-jobs" element={<CronJobsPage />} />
                  <Route path="/heartbeat" element={<HeartbeatPage />} />
                  <Route path="/platform" element={<PlatformOverviewPage />} />
                  <Route
                    path="/platform/policies"
                    element={<PlatformPoliciesPage />}
                  />
                  <Route
                    path="/platform/users"
                    element={<PlatformUsersPage />}
                  />
                  <Route
                    path="/wecom-tenants/monitoring"
                    element={<WecomTenantMonitoringPage />}
                  />
                  <Route
                    path="/wecom-tenants/monitoring/:agentId"
                    element={<WecomTenantMonitoringDetailPage />}
                  />
                  <Route
                    path="/wecom-tenants"
                    element={<WecomTenantsPage />}
                  />
                  <Route path="/skills" element={<SkillsPage />} />
                  <Route path="/skill-pool" element={<SkillPoolPage />} />
                  <Route path="/tools" element={<ToolsPage />} />
                  <Route path="/mcp" element={<MCPPage />} />
                  <Route path="/acp" element={<ACPPage />} />
                  <Route path="/ACP" element={<Navigate to="/acp" replace />} />
                  <Route path="/workspace" element={<WorkspacePage />} />
                  <Route path="/agents" element={<AgentsPage />} />
                  <Route path="/models" element={<ModelsPage />} />
                  <Route path="/environments" element={<EnvironmentsPage />} />
                  <Route path="/agent-config" element={<AgentConfigPage />} />
                  <Route path="/security" element={<SecurityPage />} />
                  <Route path="/token-usage" element={<TokenUsagePage />} />
                  <Route path="/agent-stats" element={<AgentStatsPage />} />
                  <Route
                    path="/voice-transcription"
                    element={<VoiceTranscriptionPage />}
                  />
                  <Route path="/debug" element={<DebugPage />} />
                  <Route path="/backups" element={<BackupsPage />} />
                  <Route
                    path="/plugin-manager"
                    element={<PluginManagerPage />}
                  />

                  {/* Plugin routes — dynamically injected at runtime */}
                  {pluginRoutes.map((route) => (
                    <Route
                      key={route.path}
                      path={route.path}
                      element={<route.component />}
                    />
                  ))}
                </Routes>
              </Suspense>
            </ChunkErrorBoundary>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
