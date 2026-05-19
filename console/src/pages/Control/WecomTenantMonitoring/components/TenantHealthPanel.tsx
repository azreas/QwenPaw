import { Card, Tag } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import type { WecomTenantHealthResponse } from "../../../../api/types/wecomTenant";

interface Props {
  health: WecomTenantHealthResponse | null;
}

export function TenantHealthPanel({ health }: Props) {
  const { t } = useTranslation();
  const entries = Object.entries(health?.checks ?? {});
  return (
    <Card title={t("wecomTenantMonitoring.healthDiagnosis")}>
      <dl style={{ margin: 0 }}>
        <div
          style={{
            display: "flex",
            gap: 8,
            marginBottom: 8,
          }}
        >
          <dt
            style={{
              minWidth: 100,
              color: "rgba(0,0,0,0.45)",
            }}
          >
            {t("wecomTenantMonitoring.health")}
          </dt>
          <dd style={{ margin: 0 }}>
            <Tag
              color={
                health?.status === "healthy"
                  ? "success"
                  : health?.status === "degraded"
                    ? "warning"
                    : "error"
              }
            >
              {health?.status
                ? t(
                    `wecomTenantMonitoring.${health.status}`,
                  )
                : "-"}
            </Tag>
          </dd>
        </div>
        {entries.map(([key, value]) => (
          <div
            key={key}
            style={{
              display: "flex",
              gap: 8,
              marginBottom: 8,
            }}
          >
            <dt
              style={{
                minWidth: 100,
                color: "rgba(0,0,0,0.45)",
              }}
            >
              {t(`wecomTenantMonitoring.check_${key}`, key)}
            </dt>
            <dd style={{ margin: 0 }}>
              {typeof value === "boolean" ? (
                <Tag color={value ? "success" : "error"}>
                  {value
                    ? t(
                        "wecomTenantMonitoring.checkPassed",
                      )
                    : t(
                        "wecomTenantMonitoring.checkFailed",
                      )}
                </Tag>
              ) : (
                String(value)
              )}
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
