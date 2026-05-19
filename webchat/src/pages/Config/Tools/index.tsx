import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Card, Switch, Empty, Button, Spin, message } from "antd";
import {
  EyeOutlined,
  EyeInvisibleOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useTheme } from "../../../contexts/ThemeContext";
import { toolsApi, ToolInfo } from "../../../api/modules/tools";
import styles from "./index.module.less";

export default function ToolsConfig() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);

  const loadTools = useCallback(async () => {
    setLoading(true);
    try {
      const data = await toolsApi.listTools();
      setTools(data);
    } catch (error) {
      console.error("Failed to load tools:", error);
      message.error(t("tools.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadTools();
  }, [loadTools]);

  const toggleEnabled = useCallback(
    async (tool: ToolInfo) => {
      // Optimistic update
      setTools((prev) =>
        prev.map((t) =>
          t.name === tool.name ? { ...t, enabled: !t.enabled } : t
        )
      );

      try {
        const result = await toolsApi.toggleTool(tool.name);
        message.success(
          tool.enabled ? t("tools.disableSuccess") : t("tools.enableSuccess")
        );
        // Update with server response (no full reload)
        setTools((prev) =>
          prev.map((t) => (t.name === result.name ? result : t))
        );
      } catch (error) {
        // Revert optimistic update on error
        setTools((prev) =>
          prev.map((t) =>
            t.name === tool.name ? { ...t, enabled: tool.enabled } : t
          )
        );
        message.error(t("tools.toggleError"));
      }
    },
    [t]
  );

  const toggleAsyncExecution = useCallback(
    async (tool: ToolInfo) => {
      // Optimistic update
      setTools((prev) =>
        prev.map((t) =>
          t.name === tool.name
            ? { ...t, async_execution: !t.async_execution }
            : t
        )
      );

      try {
        const result = await toolsApi.updateAsyncExecution(
          tool.name,
          !tool.async_execution
        );
        message.success(
          result.async_execution
            ? t("tools.asyncExecutionEnabled")
            : t("tools.asyncExecutionDisabled")
        );
        // Update with server response
        setTools((prev) =>
          prev.map((t) => (t.name === result.name ? result : t))
        );
      } catch (error) {
        // Revert optimistic update on error
        setTools((prev) =>
          prev.map((t) =>
            t.name === tool.name
              ? { ...t, async_execution: tool.async_execution }
              : t
          )
        );
        message.error(t("tools.toggleError"));
      }
    },
    [t]
  );

  const enableAll = useCallback(async () => {
    const disabledTools = tools.filter((tool) => !tool.enabled);
    if (disabledTools.length === 0) {
      message.info(t("tools.allEnabled"));
      return;
    }

    // Optimistic update - preserve async_execution state
    setTools((prev) => prev.map((t) => ({ ...t, enabled: true })));

    setBatchLoading(true);
    try {
      const results = await Promise.all(
        disabledTools.map((tool) => toolsApi.toggleTool(tool.name))
      );
      message.success(t("tools.enableAllSuccess"));
      // Update with server responses, but preserve async_execution
      setTools((prev) =>
        prev.map((t) => {
          const result = results.find((r) => r.name === t.name);
          return result
            ? { ...result, async_execution: t.async_execution }
            : t;
        })
      );
    } catch (error) {
      message.error(t("tools.toggleError"));
      // Reload on error to sync with server
      await loadTools();
    } finally {
      setBatchLoading(false);
    }
  }, [tools, t, loadTools]);

  const disableAll = useCallback(async () => {
    const enabledTools = tools.filter((tool) => tool.enabled);
    if (enabledTools.length === 0) {
      message.info(t("tools.allDisabled"));
      return;
    }

    // Optimistic update - preserve async_execution state
    setTools((prev) => prev.map((t) => ({ ...t, enabled: false })));

    setBatchLoading(true);
    try {
      const results = await Promise.all(
        enabledTools.map((tool) => toolsApi.toggleTool(tool.name))
      );
      message.success(t("tools.disableAllSuccess"));
      // Update with server responses, but preserve async_execution
      setTools((prev) =>
        prev.map((t) => {
          const result = results.find((r) => r.name === t.name);
          return result
            ? { ...result, async_execution: t.async_execution }
            : t;
        })
      );
    } catch (error) {
      message.error(t("tools.toggleError"));
      // Reload on error to sync with server
      await loadTools();
    } finally {
      setBatchLoading(false);
    }
  }, [tools, t, loadTools]);

  const hasDisabledTools = useMemo(
    () => tools.some((tool) => !tool.enabled),
    [tools]
  );
  const hasEnabledTools = useMemo(
    () => tools.some((tool) => tool.enabled),
    [tools]
  );

  return (
    <div className={styles.toolsPage}>
      {/* Header with title and toggle all switch */}
      <div className={styles.header}>
        <h2 className={styles.title}>{t("tools.title")}</h2>
        {tools.length > 0 && (
          <Switch
            checked={hasEnabledTools && !hasDisabledTools}
            onChange={() => (hasDisabledTools ? enableAll() : disableAll())}
            disabled={batchLoading || loading}
            checkedChildren={t("tools.enableAll")}
            unCheckedChildren={t("tools.disableAll")}
          />
        )}
      </div>

      <Spin spinning={loading}>
        {tools.length === 0 ? (
          <Empty description={t("tools.emptyState")} />
        ) : (
          <div className={styles.toolsGrid}>
            {tools.map((tool) => (
              <Card
                key={tool.name}
                className={`${styles.toolCard} ${
                  tool.enabled ? styles.enabledCard : ""
                }`}
              >
                <div className={styles.cardHeader}>
                  <h3 className={styles.toolName}>
                    {tool.icon} {tool.name}
                  </h3>
                  <div className={styles.statusContainer}>
                    <span
                      className={styles.statusDot}
                      style={{
                        backgroundColor: tool.enabled
                          ? isDark
                            ? "rgba(20, 184, 166, 1)"
                            : "rgba(20, 184, 166, 1)"
                          : isDark
                          ? "rgba(255, 255, 255, 0.2)"
                          : "#d9d9d9",
                      }}
                    />
                    <span
                      className={styles.statusText}
                      style={{
                        color: tool.enabled
                          ? isDark
                            ? "rgba(20, 184, 166, 1)"
                            : "rgba(20, 184, 166, 1)"
                          : isDark
                          ? "rgba(255, 255, 255, 0.45)"
                          : "rgba(20, 20, 19, 0.45)",
                      }}
                    >
                      {tool.enabled
                        ? t("common.enabled")
                        : t("common.disabled")}
                    </span>
                  </div>
                </div>

                <p
                  className={styles.toolDescription}
                  style={{
                    color: isDark ? "rgba(255, 255, 255, 0.65)" : "#666",
                  }}
                >
                  {tool.description}
                </p>

                <div className={styles.cardFooter}>
                  {tool.name === "execute_shell_command" && (
                    <Button
                      className={styles.toggleButton}
                      onClick={() => toggleAsyncExecution(tool)}
                      disabled={!tool.enabled}
                      icon={
                        tool.async_execution ? (
                          <ThunderboltOutlined />
                        ) : (
                          <ClockCircleOutlined />
                        )
                      }
                    >
                      {tool.async_execution
                        ? t("tools.asyncExecutionEnabled")
                        : t("tools.asyncExecutionDisabled")}
                    </Button>
                  )}
                  <Button
                    className={styles.toggleButton}
                    onClick={() => toggleEnabled(tool)}
                    icon={
                      tool.enabled ? (
                        <EyeInvisibleOutlined />
                      ) : (
                        <EyeOutlined />
                      )
                    }
                  >
                    {tool.enabled ? t("common.disable") : t("common.enable")}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Spin>
    </div>
  );
}
