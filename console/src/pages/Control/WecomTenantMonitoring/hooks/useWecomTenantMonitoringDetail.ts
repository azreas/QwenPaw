import { useCallback, useEffect, useMemo, useState } from "react";
import dayjs, { type Dayjs } from "dayjs";
import { agentsApi } from "../../../../api/modules/agents";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { AgentSummary } from "../../../../api/types/agents";
import type {
  WecomTenantAgentStats,
  WecomTenantChatListResponse,
  WecomTenantHealthResponse,
  WecomTenantSummary,
  WecomTenantTokenUsage,
} from "../../../../api/types/wecomTenant";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import { useTranslation } from "react-i18next";
import { toStatsParams } from "../model";

export function useWecomTenantMonitoringDetail(
  agentId: string | undefined,
) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [startDate, setStartDate] = useState<Dayjs>(
    dayjs().subtract(30, "day"),
  );
  const [endDate, setEndDate] = useState<Dayjs>(dayjs());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([]);
  const [agent, setAgent] = useState<AgentSummary | null>(null);
  const [health, setHealth] =
    useState<WecomTenantHealthResponse | null>(null);
  const [tokenUsage, setTokenUsage] =
    useState<WecomTenantTokenUsage | null>(null);
  const [agentStats, setAgentStats] =
    useState<WecomTenantAgentStats | null>(null);
  const [chats, setChats] =
    useState<WecomTenantChatListResponse | null>(null);

  const load = useCallback(async () => {
    if (!agentId) return;
    setLoading(true);
    setError(null);
    const params = toStatsParams(
      startDate.format("YYYY-MM-DD"),
      endDate.format("YYYY-MM-DD"),
    );
    try {
      const [
        tenantRes,
        agentRes,
        healthRes,
        tokenRes,
        statsRes,
        chatsRes,
      ] = await Promise.allSettled([
        wecomTenantApi.listWecomTenants(),
        agentsApi.listAgents(),
        wecomTenantApi.getWecomTenantHealth(agentId),
        wecomTenantApi.getWecomTenantTokenUsage(
          agentId,
          params,
        ),
        wecomTenantApi.getWecomTenantAgentStats(
          agentId,
          params,
        ),
        wecomTenantApi.listWecomTenantChats(agentId, {
          page: 1,
          page_size: 8,
        }),
      ]);

      if (tenantRes.status === "fulfilled")
        setTenants(tenantRes.value.tenants || []);
      if (agentRes.status === "fulfilled") {
        setAgent(
          agentRes.value.agents.find(
            (item) => item.id === agentId,
          ) || null,
        );
      }
      if (healthRes.status === "fulfilled")
        setHealth(healthRes.value);
      if (tokenRes.status === "fulfilled")
        setTokenUsage(tokenRes.value);
      if (statsRes.status === "fulfilled")
        setAgentStats(statsRes.value);
      if (chatsRes.status === "fulfilled")
        setChats(chatsRes.value);
    } catch (err) {
      console.error(
        "Failed to load WeCom tenant monitoring detail:",
        err,
      );
      const msg = t("wecomTenantMonitoring.loadFailed");
      message.error(msg);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [agentId, endDate, message, startDate, t]);

  useEffect(() => {
    load();
  }, [load]);

  const tenant = useMemo(
    () =>
      tenants.find((item) => item.agent_id === agentId) ||
      null,
    [agentId, tenants],
  );

  return {
    startDate,
    endDate,
    loading,
    error,
    tenant,
    agent,
    health,
    tokenUsage,
    agentStats,
    chats,
    setStartDate,
    setEndDate,
    refresh: load,
  };
}
