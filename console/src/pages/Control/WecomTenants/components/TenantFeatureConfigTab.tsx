import { useEffect, useState } from "react";
import { Alert, Tabs } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type {
  WecomLlmRoutingConfig,
  WecomModelSlot,
  WecomTenantMcpClient,
  WecomTenantSecuritySettings,
  WecomTenantTool,
} from "../../../../api/types";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import { TenantMcpSection } from "./feature/TenantMcpSection";
import { TenantModelSection } from "./feature/TenantModelSection";
import { TenantRoutingSection } from "./feature/TenantRoutingSection";
import { TenantSecuritySection } from "./feature/TenantSecuritySection";
import { TenantSystemPromptsSection } from "./feature/TenantSystemPromptsSection";
import { TenantToolsSection } from "./feature/TenantToolsSection";

interface Props {
  agentId: string;
}

function prettyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

export function TenantFeatureConfigTab({ agentId }: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [model, setModel] = useState<WecomModelSlot>({
    provider_id: "",
    model: "",
  });
  const [routingJson, setRoutingJson] = useState("{}");
  const [tools, setTools] = useState<WecomTenantTool[]>([]);
  const [mcpClients, setMcpClients] = useState<WecomTenantMcpClient[]>([]);
  const [security, setSecurity] = useState<WecomTenantSecuritySettings>({
    approval_level: "AUTO",
    tool_guard_rules: [],
  });
  const [promptsText, setPromptsText] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [
        modelData,
        routingData,
        toolsData,
        mcpData,
        securityData,
        promptsData,
      ] = await Promise.all([
        wecomTenantApi.getWecomTenantModel(agentId),
        wecomTenantApi.getWecomTenantLlmRouting(agentId),
        wecomTenantApi.listWecomTenantTools(agentId),
        wecomTenantApi.listWecomTenantMcp(agentId),
        wecomTenantApi.getWecomTenantSecurity(agentId),
        wecomTenantApi.getWecomTenantSystemPrompts(agentId),
      ]);
      setModel(modelData ?? { provider_id: "", model: "" });
      setRoutingJson(prettyJson(routingData));
      setTools(toolsData);
      setMcpClients(mcpData);
      setSecurity(securityData);
      setPromptsText((promptsData.files || []).join("\n"));
    } catch (error) {
      console.error("Failed to load tenant config:", error);
      message.error((error as Error).message || t("wecomTenants.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  const saveModel = async () => {
    setSavingKey("model");
    try {
      await wecomTenantApi.updateWecomTenantModel(agentId, model);
      message.success(t("wecomTenants.saved"));
    } finally {
      setSavingKey(null);
    }
  };

  const saveRouting = async (value: WecomLlmRoutingConfig) => {
    setSavingKey("routing");
    try {
      const saved = await wecomTenantApi.updateWecomTenantLlmRouting(agentId, value);
      setRoutingJson(prettyJson(saved));
    } finally {
      setSavingKey(null);
    }
  };

  const saveSecurity = async (value: WecomTenantSecuritySettings) => {
    setSavingKey("security");
    try {
      const saved = await wecomTenantApi.updateWecomTenantSecurity(agentId, value);
      setSecurity(saved);
    } finally {
      setSavingKey(null);
    }
  };

  const savePrompts = async () => {
    setSavingKey("prompts");
    try {
      await wecomTenantApi.updateWecomTenantSystemPrompts(agentId, {
        files: promptsText
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      message.success(t("wecomTenants.saved"));
    } finally {
      setSavingKey(null);
    }
  };

  const subTabs = [
    {
      key: "model",
      label: t("wecomTenants.configModel"),
      children: (
        <TenantModelSection
          model={model}
          loading={loading}
          saving={savingKey === "model"}
          onChange={setModel}
          onSave={saveModel}
        />
      ),
    },
    {
      key: "routing",
      label: t("wecomTenants.configRouting"),
      children: (
        <TenantRoutingSection
          value={routingJson}
          loading={loading}
          saving={savingKey === "routing"}
          onChange={setRoutingJson}
          onSave={saveRouting}
        />
      ),
    },
    {
      key: "security",
      label: t("wecomTenants.configSecurity"),
      children: (
        <TenantSecuritySection
          value={security}
          loading={loading}
          saving={savingKey === "security"}
          onChange={setSecurity}
          onSave={saveSecurity}
        />
      ),
    },
    {
      key: "prompts",
      label: t("wecomTenants.configPrompts"),
      children: (
        <TenantSystemPromptsSection
          value={promptsText}
          loading={loading}
          saving={savingKey === "prompts"}
          onChange={setPromptsText}
          onSave={savePrompts}
        />
      ),
    },
    {
      key: "tools",
      label: t("wecomTenants.configTools"),
      children: (
        <TenantToolsSection
          agentId={agentId}
          tools={tools}
          loading={loading}
          onRefresh={load}
        />
      ),
    },
    {
      key: "mcp",
      label: t("wecomTenants.configMcp"),
      children: (
        <TenantMcpSection
          agentId={agentId}
          clients={mcpClients}
          loading={loading}
          onRefresh={load}
        />
      ),
    },
  ];

  return (
    <div>
      <Alert type="info" showIcon message={t("wecomTenants.configReloadHint")} style={{ marginBottom: 12 }} />
      <Tabs items={subTabs} destroyInactiveTabPane={false} />
    </div>
  );
}
