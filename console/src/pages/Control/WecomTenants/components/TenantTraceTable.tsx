import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Input,
  Modal,
  Select,
  Table,
  Tag,
  Tooltip,
} from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type {
  WecomTenantBusinessTrace,
  BadCaseCreateRequest,
} from "../../../../api/types";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import styles from "../index.module.less";

interface Props {
  agentId: string;
  onMarked?: () => void;
}

export function TenantTraceTable({ agentId, onMarked }: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [traces, setTraces] = useState<WecomTenantBusinessTrace[]>([]);
  const [loading, setLoading] = useState(false);
  const [markingTrace, setMarkingTrace] =
    useState<WecomTenantBusinessTrace | null>(null);
  const [category, setCategory] = useState<string>("platform_runtime");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await wecomTenantApi.listTenantBusinessTraces(agentId);
      setTraces(res.items || []);
    } catch {
      message.error(t("wecomTenants.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (agentId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  const markBadCase = async () => {
    if (!markingTrace) return;
    setSaving(true);
    try {
      const body: BadCaseCreateRequest = {
        source_audit_id: markingTrace.id,
        source_request_id: markingTrace.request_id,
        source_trace_id: markingTrace.trace_id,
        category: category as BadCaseCreateRequest["category"],
        note,
      };
      await wecomTenantApi.markTenantBadCase(agentId, body);
      message.success(t("wecomTenants.badCaseMarked"));
      setMarkingTrace(null);
      setCategory("platform_runtime");
      setNote("");
      onMarked?.();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const columns: ColumnsType<WecomTenantBusinessTrace> = useMemo(
    () => [
      {
        title: t("wecomTenants.entrypoint"),
        dataIndex: "entrypoint",
        key: "entrypoint",
        width: 100,
      },
      {
        title: t("wecomTenants.abilityType"),
        dataIndex: "ability_type",
        key: "ability_type",
        width: 90,
      },
      {
        title: t("wecomTenants.abilityName"),
        dataIndex: "ability_name",
        key: "ability_name",
        width: 140,
      },
      {
        title: t("wecomTenants.durationMs"),
        key: "duration_ms",
        width: 90,
        render: (_, row) => `${Math.round(row.duration_ms)}ms`,
      },
      {
        title: t("wecomTenants.status"),
        dataIndex: "status",
        key: "status",
        width: 80,
        render: (v: string) => (
          <Tag color={v === "success" ? "green" : "red"}>{v}</Tag>
        ),
      },
      {
        title: t("wecomTenants.errorReason"),
        dataIndex: "error_reason",
        key: "error_reason",
        width: 160,
      },
      {
        title: t("wecomTenants.actorId"),
        dataIndex: "actor_id",
        key: "actor_id",
        width: 120,
      },
      {
        title: "ID",
        key: "ids",
        width: 80,
        render: (_, row) => (
          <Tooltip
            title={`request_id: ${row.request_id}\ntrace_id: ${row.trace_id}`}
          >
            <Tag>ID</Tag>
          </Tooltip>
        ),
      },
      {
        title: t("wecomTenants.createdAt"),
        dataIndex: "created_at",
        key: "created_at",
        width: 160,
        render: (v: string) => (v ? new Date(v).toLocaleString() : "-"),
      },
      {
        title: t("wecomTenants.actions"),
        key: "actions",
        width: 120,
        render: (_, row) =>
          row.status === "failure" ? (
            <Button
              size="small"
              type="primary"
              danger
              onClick={() => setMarkingTrace(row)}
            >
              {t("wecomTenants.markBadCase")}
            </Button>
          ) : null,
      },
    ],
    [t],
  );

  return (
    <>
      <Card title={t("wecomTenants.businessTraces")} bodyStyle={{ padding: 0 }}>
        <Table
          columns={columns}
          dataSource={traces}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
          size="small"
          scroll={{ x: 1200 }}
        />
      </Card>

      <Modal
        title={t("wecomTenants.markBadCase")}
        open={!!markingTrace}
        onOk={markBadCase}
        onCancel={() => setMarkingTrace(null)}
        confirmLoading={saving}
      >
        <div className={styles.badCaseForm}>
          <label>{t("wecomTenants.category")}</label>
          <Select
            value={category}
            onChange={setCategory}
            options={[
              {
                label: t("wecomTenants.platformRuntime"),
                value: "platform_runtime",
              },
              {
                label: t("wecomTenants.dataQuality"),
                value: "data_quality",
              },
              {
                label: t("wecomTenants.permissionConfig"),
                value: "permission_config",
              },
              {
                label: t("wecomTenants.productExperience"),
                value: "product_experience",
              },
            ]}
            style={{ width: "100%", marginBottom: 12 }}
          />
          <label>{t("wecomTenants.note")}</label>
          <Input.TextArea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
          />
        </div>
      </Modal>
    </>
  );
}
