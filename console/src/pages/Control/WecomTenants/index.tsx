import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import type { WecomTenantSummary } from "../../../api/types";
import { TenantDetailPane } from "./components/TenantDetailPane";
import { TenantListPane } from "./components/TenantListPane";
import { useWecomTenants } from "./hooks/useWecomTenants";
import {
  getRequestedAgentId,
  resolveSelectedTenant,
  shouldShowMissingRequestedTenant,
  shouldShowMobileDetail,
} from "./pageModel";
import styles from "./index.module.less";

type StatusFilter = "all" | "running" | "stopped" | "unhealthy";

export default function WecomTenantsPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const requestedAgentId = getRequestedAgentId(`?${searchParams.toString()}`);
  const {
    tenants,
    healthMap,
    loading,
    creating,
    actionKey,
    refresh,
    createTenant,
    runTenantAction,
    runBatchAction,
  } = useWecomTenants();
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(requestedAgentId);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);

  const selectedTenant = useMemo(
    () => resolveSelectedTenant(tenants, selectedAgentId),
    [selectedAgentId, tenants],
  );
  const mobileDetailMode = shouldShowMobileDetail(
    selectedAgentId,
    mobileDetailOpen,
  );

  useEffect(() => {
    if (requestedAgentId && requestedAgentId !== selectedAgentId) {
      setSelectedAgentId(requestedAgentId);
      return;
    }
    if (!requestedAgentId && !selectedAgentId && tenants[0]) {
      setSelectedAgentId(tenants[0].agent_id);
    }
    if (
      !requestedAgentId &&
      selectedAgentId &&
      tenants.length > 0 &&
      !tenants.some((tenant) => tenant.agent_id === selectedAgentId)
    ) {
      setSelectedAgentId(tenants[0].agent_id);
    }
  }, [requestedAgentId, selectedAgentId, tenants]);

  const handleSelectTenant = (tenant: WecomTenantSummary) => {
    setSelectedAgentId(tenant.agent_id);
    setMobileDetailOpen(true);
  };

  const handleTenantCreated = (tenant: WecomTenantSummary) => {
    setSelectedAgentId(tenant.agent_id);
  };

  const handleDeleted = async () => {
    setSelectedAgentId(null);
    setMobileDetailOpen(false);
    await refresh();
  };

  return (
    <div className={styles.page}>
      <PageHeader
        items={[{ title: t("nav.control") }, { title: t("nav.wecomTenants") }]}
      />
      <div className={styles.content}>
        <div
          className={[
            styles.workspace,
            mobileDetailMode ? styles.workspaceDetailMode : "",
          ].join(" ")}
        >
          <TenantListPane
            tenants={tenants}
            healthMap={healthMap}
            loading={loading}
            creating={creating}
            actionKey={actionKey}
            selectedAgentId={selectedTenant?.agent_id || null}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            onSelectTenant={handleSelectTenant}
            onCreateTenant={createTenant}
            onCreated={handleTenantCreated}
            onAction={runTenantAction}
            onBatchAction={runBatchAction}
            onRefresh={refresh}
          />
          {shouldShowMissingRequestedTenant(tenants, requestedAgentId) && (
            <div className={styles.missingRequestedTenant}>
              {t("wecomTenants.requestedTenantMissing", { agentId: requestedAgentId })}
            </div>
          )}
          <TenantDetailPane
            tenant={selectedTenant}
            health={selectedTenant ? healthMap[selectedTenant.agent_id] : undefined}
            actionKey={actionKey}
            onAction={runTenantAction}
            onDeleted={handleDeleted}
            onBackToList={() => setMobileDetailOpen(false)}
          />
        </div>
      </div>
    </div>
  );
}
