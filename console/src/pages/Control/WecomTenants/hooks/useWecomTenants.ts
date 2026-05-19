import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type {
  CreateWecomTenantRequest,
  WecomTenantBatchOperationResponse,
  WecomTenantDashboardResponse,
  WecomTenantHealthResponse,
  WecomTenantSummary,
} from "../../../../api/types/wecomTenant";
import { useAppMessage } from "../../../../hooks/useAppMessage";

export type TenantRuntimeAction = "start" | "stop" | "restart" | "reload";
export type TenantBatchAction = "start" | "stop" | "restart";

function toHealthMap(items: WecomTenantHealthResponse[]) {
  return items.reduce<Record<string, WecomTenantHealthResponse>>((acc, item) => {
    acc[item.agent_id] = item;
    return acc;
  }, {});
}

export function useWecomTenants() {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([]);
  const [dashboard, setDashboard] =
    useState<WecomTenantDashboardResponse | null>(null);
  const [healthMap, setHealthMap] = useState<
    Record<string, WecomTenantHealthResponse>
  >({});
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [actionKey, setActionKey] = useState<string | null>(null);

  const loadTenants = useCallback(async () => {
    const [tenantResult, healthResult, dashboardResult] = await Promise.allSettled(
      [
        wecomTenantApi.listWecomTenants(),
        wecomTenantApi.listWecomTenantHealth(),
        wecomTenantApi.getWecomTenantDashboard(),
      ],
    );

    if (tenantResult.status === "fulfilled") {
      setTenants(tenantResult.value.tenants || []);
    } else {
      console.error("Failed to load WeCom tenants:", tenantResult.reason);
      message.error(t("wecomTenants.loadFailed"));
    }

    if (healthResult.status === "fulfilled") {
      setHealthMap(toHealthMap(healthResult.value.tenants || []));
    }

    if (dashboardResult.status === "fulfilled") {
      setDashboard(dashboardResult.value);
    }
  }, [message, t]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      await loadTenants();
    } finally {
      setLoading(false);
    }
  }, [loadTenants]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const createTenant = useCallback(
    async (body: CreateWecomTenantRequest) => {
      setCreating(true);
      try {
        const tenant = await wecomTenantApi.createWecomTenant(body);
        message.success(t("wecomTenants.createSuccess"));
        await loadTenants();
        return tenant;
      } catch (error) {
        console.error("Failed to create WeCom tenant:", error);
        message.error(t("wecomTenants.createFailed"));
        return null;
      } finally {
        setCreating(false);
      }
    },
    [loadTenants, message, t],
  );

  const runTenantAction = useCallback(
    async (agentId: string, action: TenantRuntimeAction) => {
      const key = `${agentId}:${action}`;
      setActionKey(key);
      try {
        if (action === "start") {
          await wecomTenantApi.startWecomTenant(agentId);
        } else if (action === "stop") {
          await wecomTenantApi.stopWecomTenant(agentId);
        } else if (action === "restart") {
          await wecomTenantApi.restartWecomTenant(agentId);
        } else {
          await wecomTenantApi.reloadWecomTenant(agentId);
        }
        message.success(t("wecomTenants.actionSuccess"));
        await loadTenants();
      } catch (error) {
        console.error("Failed to run WeCom tenant action:", error);
        message.error((error as Error).message || t("wecomTenants.actionFailed"));
      } finally {
        setActionKey(null);
      }
    },
    [loadTenants, message, t],
  );

  const runBatchAction = useCallback(
    async (
      agentIds: string[],
      action: TenantBatchAction,
      all = false,
    ): Promise<WecomTenantBatchOperationResponse | null> => {
      if (!all && !agentIds.length) {
        message.warning(t("wecomTenants.selectTenantsFirst"));
        return null;
      }
      const key = `batch:${action}`;
      setActionKey(key);
      try {
        const body = all ? { all: true } : { agent_ids: agentIds, all: false };
        const result =
          action === "start"
            ? await wecomTenantApi.batchStartWecomTenants(body)
            : action === "stop"
              ? await wecomTenantApi.batchStopWecomTenants(body)
              : await wecomTenantApi.batchRestartWecomTenants(body);
        const failed = result.results.filter((item) => !item.success);
        if (failed.length) {
          message.warning(
            t("wecomTenants.batchPartial", { count: failed.length }),
          );
        } else {
          message.success(t("wecomTenants.batchSuccess"));
        }
        await loadTenants();
        return result;
      } catch (error) {
        console.error("Failed to run batch action:", error);
        message.error((error as Error).message || t("wecomTenants.actionFailed"));
        return null;
      } finally {
        setActionKey(null);
      }
    },
    [loadTenants, message, t],
  );

  const healthSummary = useMemo(() => {
    const items = Object.values(healthMap);
    return {
      healthy: items.filter((item) => item.status === "healthy").length,
      degraded: items.filter((item) => item.status === "degraded").length,
      unhealthy: items.filter((item) => item.status === "unhealthy").length,
    };
  }, [healthMap]);

  return {
    tenants,
    dashboard,
    healthMap,
    healthSummary,
    loading,
    creating,
    actionKey,
    refresh,
    createTenant,
    runTenantAction,
    runBatchAction,
  };
}
