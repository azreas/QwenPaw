import { Tag, Tooltip } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import type {
  WecomTenantHealthResponse,
  WecomTenantSummary,
} from "../../../../api/types/wecomTenant";

interface Props {
  tenant?: WecomTenantSummary;
  health?: WecomTenantHealthResponse;
}

export function TenantRuntimeTag({ tenant }: Pick<Props, "tenant">) {
  const { t } = useTranslation();
  if (!tenant) return null;
  return (
    <Tag color={tenant.running ? "green" : "default"}>
      {tenant.running
        ? t("wecomTenants.running")
        : t("wecomTenants.stopped")}
    </Tag>
  );
}

export function TenantHealthTag({ health, tenant }: Props) {
  const { t } = useTranslation();
  const fallbackBroken = tenant && (!tenant.exists || !tenant.initialized);
  if (!health && !fallbackBroken) return null;

  const status = health?.status ?? "unhealthy";
  const color =
    status === "healthy" ? "green" : status === "degraded" ? "orange" : "red";
  const label =
    status === "healthy"
      ? t("wecomTenants.healthy")
      : status === "degraded"
        ? t("wecomTenants.degraded")
        : t("wecomTenants.unhealthy");

  return (
    <Tooltip title={health ? t("wecomTenants.healthFromApi") : undefined}>
      <Tag color={color}>{label}</Tag>
    </Tooltip>
  );
}
