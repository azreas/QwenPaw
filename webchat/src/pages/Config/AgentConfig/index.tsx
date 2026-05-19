import { useState } from "react";
import { Button, Form, Tabs, Spin } from "antd";
import { useTranslation } from "react-i18next";
import { Breadcrumb } from "antd";
import { useAgentConfig } from "./useAgentConfig";
import {
  ReactAgentCard,
  LlmRetryCard,
  LlmRateLimiterCard,
  ContextCompactCard,
  ToolResultCompactCard,
  MemorySummaryCard,
  EmbeddingConfigCard,
} from "./components";

function AgentConfigPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("reactAgent");
  const {
    form,
    loading,
    saving,
    error,
    language,
    savingLang,
    timezone,
    savingTimezone,
    fetchConfig,
    handleSave,
    handleLanguageChange,
    handleTimezoneChange,
  } = useAgentConfig();

  const llmRetryEnabled = Form.useWatch("llm_retry_enabled", form) ?? true;
  const maxInputLength = Form.useWatch("max_input_length", form) ?? 0;

  if (loading) {
    return (
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
      }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        gap: 16,
      }}>
        <span style={{ fontSize: 14, color: "#ff4d4f" }}>{error}</span>
        <Button size="small" onClick={fetchConfig}>
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* 面包屑导航 */}
      <Breadcrumb
        style={{ marginBottom: 16, padding: "0 24px", paddingTop: 24 }}
        items={[
          { title: t("config.workspace") },
          { title: t("agentConfig.title") },
        ]}
      />

      <div style={{ flex: 1, overflow: "auto", padding: "0 24px" }}>
        <Form form={form} layout="vertical">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: "reactAgent",
                label: t("agentConfig.reactAgentTitle"),
                children: (
                  <div style={{ padding: "16px 0" }}>
                    <ReactAgentCard
                      language={language}
                      savingLang={savingLang}
                      onLanguageChange={handleLanguageChange}
                      timezone={timezone}
                      savingTimezone={savingTimezone}
                      onTimezoneChange={handleTimezoneChange}
                    />
                  </div>
                ),
              },
              {
                key: "llmRetry",
                label: t("agentConfig.llmRetryTitle"),
                children: (
                  <div style={{ padding: "16px 0" }}>
                    <LlmRetryCard llmRetryEnabled={llmRetryEnabled} />
                  </div>
                ),
              },
              {
                key: "llmRateLimiter",
                label: t("agentConfig.llmRateLimiterTitle"),
                children: (
                  <div style={{ padding: "16px 0" }}>
                    <LlmRateLimiterCard />
                  </div>
                ),
              },
              {
                key: "contextCompact",
                label: t("agentConfig.contextCompactTitle"),
                children: (
                  <div style={{ padding: "16px 0" }}>
                    <ContextCompactCard maxInputLength={maxInputLength} />
                  </div>
                ),
              },
              {
                key: "toolResultCompact",
                label: t("agentConfig.toolResultCompactTitle"),
                children: (
                  <div style={{ padding: "16px 0" }}>
                    <ToolResultCompactCard />
                  </div>
                ),
              },
              {
                key: "memorySummary",
                label: t("agentConfig.memorySummaryTitle"),
                children: (
                  <div style={{ padding: "16px 0" }}>
                    <MemorySummaryCard />
                  </div>
                ),
              },
              {
                key: "embeddingConfig",
                label: t("agentConfig.embeddingConfigTitle"),
                children: (
                  <div style={{ padding: "16px 0" }}>
                    <EmbeddingConfigCard />
                  </div>
                ),
              },
            ]}
          />
        </Form>
      </div>

      <div style={{
        display: "flex",
        justifyContent: "flex-end",
        alignItems: "center",
        padding: "16px 24px",
        borderTop: "1px solid #f0f0f0",
        background: "#fff",
        flexShrink: 0,
      }}>
        <Button
          onClick={fetchConfig}
          disabled={saving}
          style={{ marginRight: 8 }}
        >
          {t("common.reset")}
        </Button>
        <Button type="primary" onClick={handleSave} loading={saving}>
          {t("common.save")}
        </Button>
      </div>
    </div>
  );
}

export default AgentConfigPage;
