import { useState } from "react";
import { Button, Empty, Tabs, Tooltip } from "@agentscope-ai/design";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type {
  WecomTenantHealthResponse,
  WecomTenantSummary,
} from "../../../../api/types";
import type { TenantRuntimeAction } from "../hooks/useWecomTenants";
import { TenantCronTab } from "./TenantCronTab";
import { TenantFeatureConfigTab } from "./TenantFeatureConfigTab";
import { TenantFilesMemoryTab } from "./TenantFilesMemoryTab";
import { TenantHeaderActions } from "./TenantHeaderActions";
import { TenantOpsTab } from "./TenantOpsTab";
import { TenantSkillsTab } from "./TenantSkillsTab";
import { TenantSummaryTab } from "./TenantSummaryTab";
import { TenantHealthTag, TenantRuntimeTag } from "./TenantStatusTag";
import styles from "../index.module.less";

interface Props {
  tenant: WecomTenantSummary | null;
  health?: WecomTenantHealthResponse;
  actionKey: string | null;
  onAction: (agentId: string, action: TenantRuntimeAction) => Promise<void>;
  onDeleted: () => Promise<void>;
  onBackToList: () => void;
}

export function TenantDetailPane({
  tenant,
  health,
  actionKey,
  onAction,
  onDeleted,
  onBackToList,
}: Props) {
  const { t } = useTranslation();
  const [copiedPath, setCopiedPath] = useState(false);

  const handleCopyPath = async () => {
    if (!tenant) return;
    await navigator.clipboard.writeText(tenant.workspace_dir);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 1500);
  };

  if (!tenant) {
    return (
      <main className={styles.detailPane}>
        <div className={styles.emptyDetail}>
          <Empty description={t("wecomTenants.selectTenant")} />
        </div>
      </main>
    );
  }

  const agentId = tenant.agent_id;
  const tabs = [
    {
      key: "summary",
      label: t("wecomTenants.tabSummary"),
      children: <TenantSummaryTab tenant={tenant} />,
    },
    {
      key: "skills",
      label: t("wecomTenants.skills"),
      children: <TenantSkillsTab agentId={agentId} />,
    },
    {
      key: "config",
      label: t("wecomTenants.tabConfig"),
      children: <TenantFeatureConfigTab agentId={agentId} />,
    },
    {
      key: "files",
      label: t("wecomTenants.tabFiles"),
      children: <TenantFilesMemoryTab agentId={agentId} />,
    },
    {
      key: "ops",
      label: t("wecomTenants.tabOps"),
      children: <TenantOpsTab tenant={tenant} onDeleted={onDeleted} />,
    },
    {
      key: "cron",
      label: t("wecomTenants.tabCron"),
      children: <TenantCronTab agentId={agentId} running={tenant.running} />,
    },
  ];

  return (
    <main className={styles.detailPane}>
      <header className={styles.detailHeader}>
        <Button
          className={styles.mobileBackButton}
          size="small"
          icon={<ArrowLeftOutlined />}
          onClick={onBackToList}
        >
          {t("wecomTenants.backToTenantList")}
        </Button>
        <div className={styles.detailIdentity}>
          <span className={styles.detailKicker}>
            {t("wecomTenants.selectedTenant")}
          </span>
          <h2>{tenant.agent_id}</h2>
          <div className={styles.detailMeta}>
            <span>{tenant.tenant_id}</span>
            <TenantRuntimeTag tenant={tenant} />
            <TenantHealthTag tenant={tenant} health={health} />
          </div>
          <Tooltip
            title={copiedPath ? t("wecomTenants.copied") : tenant.workspace_dir}
          >
            <button
              type="button"
              className={styles.workspacePath}
              aria-label={t("wecomTenants.copyWorkspacePath")}
              onClick={handleCopyPath}
            >
              {copiedPath
                ? `✓ ${t("wecomTenants.copied")}`
                : tenant.workspace_dir}
            </button>
          </Tooltip>
        </div>
        <TenantHeaderActions
          tenant={tenant}
          actionKey={actionKey}
          onAction={onAction}
          onDeleted={onDeleted}
        />
      </header>

      <Tabs
        className={styles.detailTabs}
        items={tabs}
        destroyInactiveTabPane={false}
      />
    </main>
  );
}
