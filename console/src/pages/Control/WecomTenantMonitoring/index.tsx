import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Spin } from "antd";
import { Empty } from "@agentscope-ai/design";
import { MonitoringFilters } from "./components/MonitoringFilters";
import { MonitoringKpis } from "./components/MonitoringKpis";
import { TokenAnalysisPanel } from "./components/TokenAnalysisPanel";
import { TenantStatusMatrix } from "./components/TenantStatusMatrix";
import { TenantAttentionPanel } from "./components/TenantAttentionPanel";
import { useWecomTenantMonitoring } from "./hooks/useWecomTenantMonitoring";
import styles from "./index.module.less";

export default function WecomTenantMonitoringPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const {
    loading,
    filters,
    setFilters,
    refresh,
    kpis,
    allRows,
    filteredRows,
    attentionItems,
    tokenModelRows,
    tokenDateRows,
  } = useWecomTenantMonitoring();

  const handleDrilldown = useCallback(
    (agentId: string) => {
      navigate(`/wecom-tenants/monitoring/${encodeURIComponent(agentId)}`);
    },
    [navigate],
  );

  if (loading && allRows.length === 0) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingWrap}>
          <Spin size="large" />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <MonitoringFilters
          filters={filters}
          onChange={setFilters}
          onRefresh={refresh}
          loading={loading}
        />

        {allRows.length === 0 ? (
          <Empty description={t("wecomTenantMonitoring.noTenants")} />
        ) : (
          <>
            <MonitoringKpis kpis={kpis} />

            <TokenAnalysisPanel
              modelRows={tokenModelRows}
              dateRows={tokenDateRows}
            />

            <TenantStatusMatrix
              rows={filteredRows}
              onDrilldown={handleDrilldown}
            />

            <TenantAttentionPanel
              items={attentionItems}
              onDrilldown={handleDrilldown}
            />
          </>
        )}
      </div>
    </div>
  );
}
