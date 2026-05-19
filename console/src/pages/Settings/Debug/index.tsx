import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Button,
  Card,
  Input,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { PageHeader } from "@/components/PageHeader";
import {
  runtimeApi,
  summarizeReadiness,
  type RuntimeReadinessResponse,
} from "@/api/modules/runtime";
import { useDebugLogs, backendLevelColor } from "./useDebugLogs";
import { LogViewer } from "./components";
import styles from "./index.module.less";

const { Text } = Typography;

export default function DebugPage() {
  const { t } = useTranslation();
  const {
    backendLogs,
    initialLoading,
    backendError,
    autoRefresh,
    setAutoRefresh,
    backendNewestFirst,
    setBackendNewestFirst,
    backendLevel,
    setBackendLevel,
    backendQuery,
    setBackendQuery,
    filteredBackendLines,
    loadBackendLogs,
    handleCopyBackend,
  } = useDebugLogs();

  const [healthStatus, setHealthStatus] = useState<string>("loading");
  const [readiness, setReadiness] =
    useState<RuntimeReadinessResponse | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [metricsPreview, setMetricsPreview] = useState<string>("");

  const readinessSummary = useMemo(
    () => (readiness ? summarizeReadiness(readiness) : null),
    [readiness],
  );

  async function loadRuntimeStatus() {
    setRuntimeError(null);
    const [healthResult, readyResult, metricsResult] = await Promise.allSettled([
      runtimeApi.getHealth(),
      runtimeApi.getReady(),
      runtimeApi.getMetrics(),
    ]);

    if (healthResult.status === "fulfilled") {
      setHealthStatus(healthResult.value.status);
    } else {
      setHealthStatus("error");
    }

    if (readyResult.status === "fulfilled") {
      setReadiness(readyResult.value);
    } else {
      setReadiness(null);
    }

    if (metricsResult.status === "fulfilled") {
      setMetricsPreview(metricsResult.value.split("\n").slice(0, 6).join("\n"));
    } else {
      setMetricsPreview("");
    }

    const errors: string[] = [];
    if (healthResult.status === "rejected") errors.push(`health: ${String(healthResult.reason)}`);
    if (readyResult.status === "rejected") errors.push(`ready: ${String(readyResult.reason)}`);
    if (metricsResult.status === "rejected") errors.push(`metrics: ${String(metricsResult.reason)}`);
    setRuntimeError(errors.length ? errors.join("; ") : null);
  }

  useEffect(() => {
    void loadRuntimeStatus();
  }, []);

  return (
    <div className={styles.debugPage}>
      <PageHeader
        parent={t("nav.settings")}
        current={t("debug.title", "Debug")}
      />

      <div className={styles.content}>
        <Alert
          type="info"
          showIcon
          className={styles.tipAlert}
          message={t(
            "debug.desc",
            "View backend daemon log file to help diagnose issues. Logs refresh automatically while this page is open.",
          )}
        />
        <Card
          title={t("debug.runtime.title", "Runtime status")}
          extra={
            <Button onClick={() => void loadRuntimeStatus()}>
              {t("debug.actions.refreshRuntime", "Refresh runtime")}
            </Button>
          }
        >
          <div className={styles.runtimeGrid}>
            <div className={styles.runtimeItem}>
              <Text type="secondary">
                {t("debug.runtime.health", "Health")}
              </Text>
              <Tag color={healthStatus === "ok" ? "green" : "red"}>
                {healthStatus}
              </Tag>
            </div>
            <div className={styles.runtimeItem}>
              <Text type="secondary">
                {t("debug.runtime.ready", "Ready")}
              </Text>
              <Tag color={readinessSummary?.ready ? "green" : "red"}>
                {readinessSummary?.status || "unknown"}
              </Tag>
            </div>
            <div className={styles.runtimeItemWide}>
              <Text type="secondary">
                {t("debug.runtime.metricsPreview", "Metrics preview")}
              </Text>
              <pre className={styles.metricsPreview}>{metricsPreview}</pre>
            </div>
          </div>
          {readinessSummary?.failedComponents.length ? (
            <Alert
              type="error"
              showIcon
              message={`${t("debug.runtime.failedComponents", "Down components")}: ${readinessSummary.failedComponents.join(", ")}`}
            />
          ) : null}
          {runtimeError ? (
            <Alert type="error" showIcon message={runtimeError} />
          ) : null}
        </Card>
        <Card
          title={t("debug.backend.title", "Backend logs")}
          extra={
            <Space size="middle">
              <Text type="secondary">
                {t("debug.backend.newestFirst", "Newest first")}
              </Text>
              <Switch
                checked={backendNewestFirst}
                onChange={setBackendNewestFirst}
              />
              <Text type="secondary">
                {t("debug.backend.autoRefresh", "Auto refresh")}
              </Text>
              <Switch checked={autoRefresh} onChange={setAutoRefresh} />
            </Space>
          }
        >
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <div className={styles.toolbar}>
              <div className={styles.toolbarLeft}>
                <Select
                  style={{ width: 160 }}
                  value={backendLevel}
                  onChange={(v) => setBackendLevel(v)}
                  options={[
                    { value: "all", label: t("debug.level.all", "All") },
                    {
                      value: "error",
                      label: (
                        <Tag color={backendLevelColor("error")}>ERROR</Tag>
                      ),
                    },
                    {
                      value: "warning",
                      label: (
                        <Tag color={backendLevelColor("warning")}>WARNING</Tag>
                      ),
                    },
                    {
                      value: "info",
                      label: <Tag color={backendLevelColor("info")}>INFO</Tag>,
                    },
                    {
                      value: "debug",
                      label: (
                        <Tag color={backendLevelColor("debug")}>DEBUG</Tag>
                      ),
                    },
                  ]}
                />
                <Input
                  style={{ width: 320 }}
                  value={backendQuery}
                  onChange={(e) => setBackendQuery(e.target.value)}
                  placeholder={t(
                    "debug.backend.searchPlaceholder",
                    "Search backend logs...",
                  )}
                  allowClear
                />
                {backendLogs?.updated_at && (
                  <Text type="secondary">
                    {t("debug.backend.updatedAt", "Updated at")}:{" "}
                    {dayjs(backendLogs.updated_at * 1000).format(
                      "YYYY-MM-DD HH:mm:ss",
                    )}
                  </Text>
                )}
              </div>
              <div className={styles.toolbarRight}>
                <Button
                  onClick={() => void loadBackendLogs({ successToast: true })}
                >
                  {t("debug.actions.refreshBackend", "Refresh backend logs")}
                </Button>
                <Button onClick={() => void handleCopyBackend()}>
                  {t("debug.actions.copyBackend", "Copy backend logs")}
                </Button>
              </div>
            </div>

            {backendLogs?.path && (
              <div className={styles.logPath}>
                <Text type="secondary" className={styles.logPathLabel}>
                  {t("debug.backend.path", "Log file")}
                </Text>
                <code className={styles.logPathValue}>{backendLogs.path}</code>
              </div>
            )}

            {backendError ? (
              <Alert message={backendError} type="error" showIcon />
            ) : !backendLogs?.exists ? (
              <Alert
                message={t(
                  "debug.backend.notFound",
                  "Backend log file was not found yet.",
                )}
                type="warning"
                showIcon
              />
            ) : null}

            <LogViewer
              lines={filteredBackendLines}
              query={backendQuery}
              loading={initialLoading}
            />
          </Space>
        </Card>
      </div>
    </div>
  );
}
