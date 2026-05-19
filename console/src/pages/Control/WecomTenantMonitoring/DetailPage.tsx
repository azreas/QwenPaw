import { Button, Card, Empty } from "@agentscope-ai/design";
import { Alert, Spin } from "antd";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { getManagementPath } from "./model";
import { TenantChatsPanel } from "./components/TenantChatsPanel";
import { TenantHealthPanel } from "./components/TenantHealthPanel";
import { TenantUsagePanel } from "./components/TenantUsagePanel";
import { useWecomTenantMonitoringDetail } from "./hooks/useWecomTenantMonitoringDetail";
import styles from "./detail.module.less";

export default function WecomTenantMonitoringDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { agentId } = useParams<{
    agentId: string;
  }>();
  const detail =
    useWecomTenantMonitoringDetail(agentId);

  if (detail.loading && !detail.tenant) {
    return <Spin />;
  }

  if (!detail.tenant) {
    return (
      <div className={styles.page}>
        <PageHeader
          items={[
            { title: t("nav.control") },
            {
              title: t("wecomTenantMonitoring.title"),
              onClick: () => navigate("/wecom-tenants/monitoring"),
            },
            {
              title: t(
                "wecomTenantMonitoring.detailTitle",
              ),
            },
          ]}
        />
        <div className={styles.content}>
          <Empty
            description={t(
              "wecomTenantMonitoring.notFound",
            )}
          >
            <Button
              onClick={() =>
                navigate("/wecom-tenants/monitoring")
              }
            >
              {t(
                "wecomTenantMonitoring.backToMonitoring",
              )}
            </Button>
          </Empty>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <PageHeader
        items={[
          { title: t("nav.control") },
          {
            title: t("wecomTenantMonitoring.title"),
            onClick: () => navigate("/wecom-tenants/monitoring"),
          },
          { title: detail.tenant.agent_id },
        ]}
      />
      <div className={styles.content}>
        {detail.error && (
          <Alert
            type="error"
            showIcon
            message={detail.error}
          />
        )}
        <Card
          title={t("wecomTenantMonitoring.identity")}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "8px 16px",
              marginBottom: 12,
            }}
          >
            <div>
              <span style={{ color: "rgba(0,0,0,0.45)" }}>
                {t("wecomTenantMonitoring.agentIdLabel")}:{" "}
              </span>
              {detail.tenant.agent_id}
            </div>
            <div>
              <span style={{ color: "rgba(0,0,0,0.45)" }}>
                {t("wecomTenantMonitoring.tenantIdLabel")}:{" "}
              </span>
              {detail.tenant.tenant_id}
            </div>
            <div>
              <span style={{ color: "rgba(0,0,0,0.45)" }}>
                {t("wecomTenantMonitoring.agentNameLabel")}:{" "}
              </span>
              {detail.agent?.name || t("wecomTenantMonitoring.agentMissing")}
            </div>
            <div>
              <span style={{ color: "rgba(0,0,0,0.45)" }}>
                {t("wecomTenantMonitoring.model")}:{" "}
              </span>
              {detail.agent?.active_model
                ? `${detail.agent.active_model.provider_id} / ${detail.agent.active_model.model}`
                : "-"}
            </div>
          </div>
          <Button
            type="primary"
            onClick={() =>
              navigate(
                getManagementPath(
                  detail.tenant!.agent_id,
                ),
              )
            }
          >
            {t("wecomTenantMonitoring.goManage")}
          </Button>
        </Card>
        <div className={styles.detailGrid}>
          <TenantHealthPanel
            health={detail.health}
          />
          <TenantUsagePanel
            tokenUsage={detail.tokenUsage}
            agentStats={detail.agentStats}
          />
        </div>
        <TenantChatsPanel agentId={detail.tenant.agent_id} chats={detail.chats} />
      </div>
    </div>
  );
}
