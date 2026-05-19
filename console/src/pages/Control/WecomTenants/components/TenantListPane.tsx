import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Input, Modal, Select, Switch, Table } from "@agentscope-ai/design";
import { ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type {
  CreateWecomTenantRequest,
  WecomTenantBatchOperationResponse,
  WecomTenantHealthResponse,
  WecomTenantOperationResult,
  WecomTenantSummary,
} from "../../../../api/types";
import type {
  TenantBatchAction,
  TenantRuntimeAction,
} from "../hooks/useWecomTenants";
import {
  createBatchResultColumns,
  createTenantColumns,
} from "./list/tenantListColumns";
import styles from "../index.module.less";

type StatusFilter = "all" | "running" | "stopped" | "unhealthy";

interface Props {
  tenants: WecomTenantSummary[];
  healthMap: Record<string, WecomTenantHealthResponse>;
  loading: boolean;
  creating: boolean;
  actionKey: string | null;
  selectedAgentId: string | null;
  statusFilter: StatusFilter;
  onStatusFilterChange: (value: StatusFilter) => void;
  onSelectTenant: (tenant: WecomTenantSummary) => void;
  onCreateTenant: (body: CreateWecomTenantRequest) => Promise<unknown>;
  onCreated?: (tenant: WecomTenantSummary) => void;
  onAction: (agentId: string, action: TenantRuntimeAction) => Promise<void>;
  onBatchAction: (
    agentIds: string[],
    action: TenantBatchAction,
    all?: boolean,
  ) => Promise<WecomTenantBatchOperationResponse | null>;
  onRefresh: () => Promise<void>;
}

export function TenantListPane(props: Props) {
  const { t } = useTranslation();
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const [tenantId, setTenantId] = useState("");
  const [startAfterCreate, setStartAfterCreate] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchResult, setBatchResult] = useState<{
    action: TenantBatchAction;
    results: WecomTenantOperationResult[];
  } | null>(null);

  const handleQueryChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const value = event.target.value;
      setQueryInput(value);
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => setQuery(value), 300);
    },
    [],
  );

  useEffect(() => () => clearTimeout(debounceRef.current), []);

  const filteredTenants = useMemo(() => {
    const text = query.trim().toLowerCase();
    return props.tenants.filter((tenant) => {
      const health = props.healthMap[tenant.agent_id];
      const matchesText =
        !text ||
        tenant.agent_id.toLowerCase().includes(text) ||
        tenant.tenant_id.toLowerCase().includes(text);
      const matchesStatus =
        props.statusFilter === "all" ||
        (props.statusFilter === "running" && tenant.running) ||
        (props.statusFilter === "stopped" && !tenant.running) ||
        (props.statusFilter === "unhealthy" &&
          (health?.status === "unhealthy" ||
            !tenant.exists ||
            !tenant.initialized));
      return matchesText && matchesStatus;
    });
  }, [props.healthMap, props.statusFilter, props.tenants, query]);

  const handleCreate = async () => {
    const value = tenantId.trim();
    if (!value) return;
    const result = await props.onCreateTenant({
      tenant_id: value,
      start: startAfterCreate,
    });
    if (result) {
      setTenantId("");
      props.onCreated?.(result as WecomTenantSummary);
    }
  };

  const copyPath = async (value: string, event: React.MouseEvent) => {
    event.stopPropagation();
    await navigator.clipboard.writeText(value);
  };

  const runBatch = async (action: TenantBatchAction, all = false) => {
    const result = await props.onBatchAction(
      selectedRowKeys as string[],
      action,
      all,
    );
    if (result) {
      setBatchResult({ action, results: result.results });
      if (!all) setSelectedRowKeys([]);
    }
  };

  const confirmRunAll = (action: TenantBatchAction) => {
    Modal.confirm({
      title: t(`wecomTenants.batchAllConfirmTitle_${action}`),
      content: t("wecomTenants.batchAllConfirmContent", {
        count: props.tenants.length,
      }),
      okText: t(`wecomTenants.batchAll_${action}`),
      cancelText: t("common.cancel"),
      onOk: () => runBatch(action, true),
    });
  };

  const resultColumns = createBatchResultColumns(t);
  const columns = createTenantColumns({
    t,
    styles,
    healthMap: props.healthMap,
    onAction: props.onAction,
    onCopyPath: copyPath,
  });

  return (
    <aside className={styles.listPane}>
      <div className={styles.panelHeader}>
        <div className={styles.panelTitle}>
          <span>{t("wecomTenants.tenantDirectory")}</span>
          <strong>{t("nav.wecomTenants")}</strong>
        </div>
        <span className={styles.panelCount}>
          {t("wecomTenants.filteredTenantCount", {
            shown: filteredTenants.length,
            total: props.tenants.length,
          })}
        </span>
      </div>

      <div className={styles.listControls}>
        <div className={styles.listToolbar}>
          <Input
            value={queryInput}
            onChange={handleQueryChange}
            aria-label={t("wecomTenants.searchPlaceholder")}
            placeholder={t("wecomTenants.searchPlaceholder")}
          />
          <Select
            value={props.statusFilter}
            onChange={props.onStatusFilterChange}
            options={[
              { value: "all", label: t("common.all") },
              { value: "running", label: t("wecomTenants.running") },
              { value: "stopped", label: t("wecomTenants.stopped") },
              { value: "unhealthy", label: t("wecomTenants.unhealthy") },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={props.onRefresh}>
            {t("common.refresh")}
          </Button>
        </div>

        <div className={styles.createRow}>
          <Input
            value={tenantId}
            onChange={(event) => setTenantId(event.target.value)}
            onPressEnter={handleCreate}
            aria-label={t("wecomTenants.tenantIdPlaceholder")}
            placeholder={t("wecomTenants.tenantIdPlaceholder")}
          />
          <label className={styles.inlineSwitch}>
            <Switch checked={startAfterCreate} onChange={setStartAfterCreate} />
            <span>{t("wecomTenants.startAfterCreate")}</span>
          </label>
          <Button
            type="primary"
            loading={props.creating}
            disabled={!tenantId.trim()}
            onClick={handleCreate}
          >
            {t("wecomTenants.create")}
          </Button>
        </div>
      </div>

      <div className={styles.batchBar}>
        <span>
          {t("wecomTenants.selectedCount", { count: selectedRowKeys.length })}
        </span>
        <div className={styles.batchActions}>
          {(["start", "stop", "restart"] as TenantBatchAction[]).map(
            (action) => (
              <Button
                key={action}
                size="small"
                disabled={!selectedRowKeys.length}
                loading={props.actionKey === `batch:${action}`}
                onClick={() => runBatch(action)}
              >
                {t(`wecomTenants.batch_${action}`)}
              </Button>
            ),
          )}
          {(["start", "stop", "restart"] as TenantBatchAction[]).map(
            (action) => (
              <Button
                key={`all-${action}`}
                size="small"
                disabled={!props.tenants.length}
                loading={props.actionKey === `batch:${action}`}
                onClick={() => confirmRunAll(action)}
              >
                {t(`wecomTenants.batchAll_${action}`)}
              </Button>
            ),
          )}
        </div>
      </div>

      <Table<WecomTenantSummary>
        columns={columns}
        dataSource={filteredTenants}
        loading={props.loading}
        rowKey="agent_id"
        size="small"
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        rowClassName={(record) =>
          record.agent_id === props.selectedAgentId ? styles.selectedRow : ""
        }
        onRow={(tenant) => ({
          onClick: () => props.onSelectTenant(tenant),
        })}
        pagination={{ pageSize: 8, showSizeChanger: false }}
        scroll={{ x: 700 }}
      />

      <Modal
        title={t("wecomTenants.batchResultsTitle", {
          action: batchResult
            ? t(`wecomTenants.batch_${batchResult.action}`)
            : "",
        })}
        open={Boolean(batchResult)}
        width={720}
        footer={null}
        onCancel={() => setBatchResult(null)}
      >
        <Table<WecomTenantOperationResult>
          columns={resultColumns}
          dataSource={batchResult?.results || []}
          rowKey="agent_id"
          size="small"
          pagination={{ pageSize: 8, showSizeChanger: false }}
        />
      </Modal>
    </aside>
  );
}
