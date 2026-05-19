import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import { agentsApi } from "../../../../api/modules/agents";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { AgentSummary } from "../../../../api/types/agents";
import type { TokenUsageSummary } from "../../../../api/types/tokenUsage";
import type {
  WecomTenantHealthResponse,
  WecomTenantSummary,
} from "../../../../api/types/wecomTenant";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import type { MonitoringFilters } from "../model";
import {
  buildAttentionItems,
  buildStatsParams,
  buildTenantRows,
  buildTokenDateRows,
  buildTokenModelRows,
  computeKpis,
  filterRows,
} from "../model";

function toHealthMap(items: WecomTenantHealthResponse[]) {
  return items.reduce<Record<string, WecomTenantHealthResponse>>(
    (acc, item) => {
      acc[item.agent_id] = item;
      return acc;
    },
    {},
  );
}

export function useWecomTenantMonitoring() {
  const { t } = useTranslation();
  const { message } = useAppMessage();

  // ---- 原始数据 ----
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([]);
  const [healthMap, setHealthMap] = useState<
    Record<string, WecomTenantHealthResponse>
  >({});
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [globalTokens, setGlobalTokens] =
    useState<TokenUsageSummary | null>(null);
  const [tokenMap, setTokenMap] = useState<
    Record<string, TokenUsageSummary>
  >({});

  // ---- UI 状态 ----
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<MonitoringFilters>({
    status: "all",
    health: "all",
    dateRange: [
      dayjs().subtract(30, "day").format("YYYY-MM-DD"),
      dayjs().format("YYYY-MM-DD"),
    ],
  });

  // ---- 加载数据 ----
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = buildStatsParams(filters.dateRange);

      // 并行加载基础数据
      const [tenantRes, healthRes, agentRes, globalTokenRes] =
        await Promise.allSettled([
          wecomTenantApi.listWecomTenants(),
          wecomTenantApi.listWecomTenantHealth(),
          agentsApi.listAgents(),
          wecomTenantApi.getGlobalWecomTenantTokenUsage(params),
        ]);

      const tenantList =
        tenantRes.status === "fulfilled"
          ? tenantRes.value.tenants || []
          : [];
      const healthList =
        healthRes.status === "fulfilled"
          ? healthRes.value.tenants || []
          : [];
      const agentList =
        agentRes.status === "fulfilled"
          ? agentRes.value.agents || []
          : [];
      const globalTokenData =
        globalTokenRes.status === "fulfilled"
          ? globalTokenRes.value
          : null;

      setTenants(tenantList);
      setHealthMap(toHealthMap(healthList));
      setAgents(agentList);
      setGlobalTokens(globalTokenData);

      // 为每个租户加载 token 用量
      if (tenantList.length > 0) {
        const tokenResults = await Promise.allSettled(
          tenantList.map((t) =>
            wecomTenantApi.getWecomTenantTokenUsage(t.agent_id, params),
          ),
        );
        const map: Record<string, TokenUsageSummary> = {};
        tenantList.forEach((t, i) => {
          const result = tokenResults[i];
          if (result.status === "fulfilled") {
            map[t.agent_id] = result.value;
          }
        });
        setTokenMap(map);
      } else {
        setTokenMap({});
      }

      if (
        tenantRes.status === "rejected" ||
        agentRes.status === "rejected"
      ) {
        message.error(t("wecomTenantMonitoring.loadFailed"));
      }
    } finally {
      setLoading(false);
    }
  }, [filters.dateRange, message, t]);

  useEffect(() => {
    load();
  }, [load]);

  // ---- 派生数据 ----
  const allRows = useMemo(
    () => buildTenantRows(tenants, healthMap, agents, tokenMap),
    [tenants, healthMap, agents, tokenMap],
  );

  const filteredRows = useMemo(
    () => filterRows(allRows, filters),
    [allRows, filters],
  );

  const kpis = useMemo(
    () => computeKpis(allRows, agents),
    [allRows, agents],
  );

  const attentionItems = useMemo(
    () => buildAttentionItems(allRows, agents),
    [allRows, agents],
  );

  const tokenModelRows = useMemo(
    () => buildTokenModelRows(globalTokens),
    [globalTokens],
  );

  const tokenDateRows = useMemo(
    () => buildTokenDateRows(globalTokens),
    [globalTokens],
  );

  return {
    loading,
    filters,
    setFilters,
    refresh: load,
    kpis,
    allRows,
    filteredRows,
    attentionItems,
    tokenModelRows,
    tokenDateRows,
  };
}
