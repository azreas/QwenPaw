import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, Input, Switch, Tooltip } from "@agentscope-ai/design";
import { Alert, Empty, Spin, Tag } from "antd";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { WecomTenantSummary } from "../../../../api/types/wecomTenant";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import styles from "../index.module.less";

type TenantAction = "start" | "stop" | "restart";

function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function getTenantHealth(tenant: WecomTenantSummary): "ok" | "warning" {
  return tenant.exists && tenant.initialized ? "ok" : "warning";
}

interface SummaryProps {
  tenants: WecomTenantSummary[];
}

function TenantSummary({ tenants }: SummaryProps) {
  const { t } = useTranslation();
  const stats = useMemo(() => {
    const running = tenants.filter((item) => item.running).length;
    const broken = tenants.filter(
      (item) => !item.exists || !item.initialized,
    ).length;
    return {
      total: tenants.length,
      running,
      stopped: tenants.length - running,
      broken,
    };
  }, [tenants]);

  return (
    <div className={styles.wecomTenantStats}>
      <div>
        <strong>{stats.total}</strong>
        <span>{t("channels.wecomTenantTotal")}</span>
      </div>
      <div>
        <strong>{stats.running}</strong>
        <span>{t("channels.wecomTenantRunning")}</span>
      </div>
      <div>
        <strong>{stats.stopped}</strong>
        <span>{t("channels.wecomTenantStopped")}</span>
      </div>
      <div>
        <strong>{stats.broken}</strong>
        <span>{t("channels.wecomTenantBroken")}</span>
      </div>
    </div>
  );
}

export function WecomTenantManager() {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [tenantId, setTenantId] = useState("");
  const [startAfterCreate, setStartAfterCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [actionKey, setActionKey] = useState<string | null>(null);

  const loadTenants = useCallback(async () => {
    setLoading(true);
    try {
      const data = await wecomTenantApi.listWecomTenants();
      setTenants(data.tenants || []);
    } catch (error) {
      console.error("Failed to load WeCom tenants:", error);
      message.error(t("channels.wecomTenantLoadFailed"));
    } finally {
      setLoading(false);
    }
  }, [message, t]);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  const handleCreate = async () => {
    const value = tenantId.trim();
    if (!value) {
      message.warning(t("channels.wecomTenantIdRequired"));
      return;
    }

    setCreating(true);
    try {
      await wecomTenantApi.createWecomTenant({
        tenant_id: value,
        start: startAfterCreate,
      });
      setTenantId("");
      message.success(t("channels.wecomTenantCreateSuccess"));
      await loadTenants();
    } catch (error) {
      console.error("Failed to create WeCom tenant:", error);
      message.error(t("channels.wecomTenantCreateFailed"));
    } finally {
      setCreating(false);
    }
  };

  const handleAction = async (
    tenant: WecomTenantSummary,
    action: TenantAction,
  ) => {
    const key = `${tenant.agent_id}:${action}`;
    setActionKey(key);
    try {
      if (action === "start") {
        await wecomTenantApi.startWecomTenant(tenant.agent_id);
      } else if (action === "stop") {
        await wecomTenantApi.stopWecomTenant(tenant.agent_id);
      } else {
        await wecomTenantApi.restartWecomTenant(tenant.agent_id);
      }
      message.success(t("channels.wecomTenantActionSuccess"));
      await loadTenants();
    } catch (error) {
      console.error("Failed to update WeCom tenant:", error);
      message.error(t("channels.wecomTenantActionFailed"));
    } finally {
      setActionKey(null);
    }
  };

  const copyText = async (value: string) => {
    await navigator.clipboard.writeText(value);
    message.success(t("channels.wecomTenantCopied"));
  };

  return (
    <section className={styles.wecomTenantManager}>
      <div className={styles.wecomTenantHeader}>
        <div>
          <h3>{t("channels.wecomTenantManagerTitle")}</h3>
          <p>{t("channels.wecomTenantManagerDesc")}</p>
        </div>
        <Button size="small" onClick={loadTenants} loading={loading}>
          {t("common.refresh")}
        </Button>
      </div>

      <Alert
        type="info"
        showIcon
        className={styles.wecomTenantNotice}
        message={t("channels.wecomTenantNotice")}
      />

      <TenantSummary tenants={tenants} />

      <div className={styles.wecomTenantCreate}>
        <Input
          value={tenantId}
          onChange={(event) => setTenantId(event.target.value)}
          placeholder={t("channels.wecomTenantIdPlaceholder")}
          onPressEnter={handleCreate}
        />
        <label className={styles.wecomTenantCreateSwitch}>
          <Switch
            checked={startAfterCreate}
            onChange={setStartAfterCreate}
          />
          <span>{t("channels.wecomTenantStartAfterCreate")}</span>
        </label>
        <Button type="primary" loading={creating} onClick={handleCreate}>
          {startAfterCreate
            ? t("channels.wecomTenantCreateAndStart")
            : t("channels.wecomTenantCreate")}
        </Button>
      </div>

      {loading ? (
        <div className={styles.wecomTenantLoading}>
          <Spin />
        </div>
      ) : tenants.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t("channels.wecomTenantEmpty")}
        />
      ) : (
        <div className={styles.wecomTenantList}>
          {tenants.map((tenant) => {
            const health = getTenantHealth(tenant);
            return (
              <div className={styles.wecomTenantItem} key={tenant.agent_id}>
                <div className={styles.wecomTenantItemMain}>
                  <div className={styles.wecomTenantTitleRow}>
                    <strong>{tenant.agent_id}</strong>
                    <Tag color={tenant.running ? "green" : "default"}>
                      {tenant.running
                        ? t("channels.wecomTenantRunning")
                        : t("channels.wecomTenantStopped")}
                    </Tag>
                    {health === "warning" && (
                      <Tag color="orange">
                        {t("channels.wecomTenantBroken")}
                      </Tag>
                    )}
                  </div>
                  <div className={styles.wecomTenantMeta}>
                    <span>{tenant.tenant_id}</span>
                    <span>{t("channels.wecomTenantChats", {
                      count: tenant.chat_count,
                    })}</span>
                    <span>{t("channels.wecomTenantJobs", {
                      count: tenant.job_count,
                    })}</span>
                    <span>{formatDate(tenant.updated_at)}</span>
                  </div>
                  <Tooltip title={tenant.workspace_dir}>
                    <button
                      className={styles.wecomTenantPath}
                      type="button"
                      onClick={() => copyText(tenant.workspace_dir)}
                    >
                      {tenant.workspace_dir}
                    </button>
                  </Tooltip>
                </div>
                <div className={styles.wecomTenantActions}>
                  <Button
                    size="small"
                    disabled={tenant.running || !tenant.exists}
                    loading={actionKey === `${tenant.agent_id}:start`}
                    onClick={() => handleAction(tenant, "start")}
                  >
                    {t("channels.wecomTenantStart")}
                  </Button>
                  <Button
                    size="small"
                    disabled={!tenant.running}
                    loading={actionKey === `${tenant.agent_id}:stop`}
                    onClick={() => handleAction(tenant, "stop")}
                  >
                    {t("channels.wecomTenantStop")}
                  </Button>
                  <Button
                    size="small"
                    disabled={!tenant.exists}
                    loading={actionKey === `${tenant.agent_id}:restart`}
                    onClick={() => handleAction(tenant, "restart")}
                  >
                    {t("channels.wecomTenantRestart")}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
