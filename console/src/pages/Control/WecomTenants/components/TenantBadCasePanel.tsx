import { useCallback, useEffect, useMemo, useState } from "react";
import { Card, Select, Table } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type {
  WecomTenantBadCase,
  BadCaseUpdateRequest,
} from "../../../../api/types";
import { useAppMessage } from "../../../../hooks/useAppMessage";

const STATUS_COLORS: Record<string, string> = {
  open: "orange",
  triaged: "blue",
  transferred: "gold",
  resolved: "green",
  ignored: "default",
};
const CATEGORY_COLORS: Record<string, string> = {
  platform_runtime: "red",
  data_quality: "blue",
  permission_config: "orange",
  product_experience: "purple",
};
const CATEGORY_I18N: Record<string, string> = {
  platform_runtime: "platformRuntime",
  data_quality: "dataQuality",
  permission_config: "permissionConfig",
  product_experience: "productExperience",
};

interface Props {
  agentId: string;
  refreshKey?: number;
}

export function TenantBadCasePanel({ agentId, refreshKey = 0 }: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [cases, setCases] = useState<WecomTenantBadCase[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await wecomTenantApi.listTenantBadCases(agentId);
      setCases(res.items || []);
    } catch {
      message.error(t("wecomTenants.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [agentId, t, message]);

  useEffect(() => {
    if (agentId) load();
  }, [agentId, load, refreshKey]);

  const updateBadCase = useCallback(
    async (caseId: string, update: BadCaseUpdateRequest) => {
      try {
        await wecomTenantApi.updateTenantBadCase(agentId, caseId, update);
        await load();
      } catch (e) {
        message.error((e as Error).message);
      }
    },
    [agentId, load, message],
  );

  const visibleCases = useMemo(
    () =>
      cases.filter((c) =>
        ["open", "triaged", "transferred"].includes(c.status),
      ),
    [cases],
  );

  const columns: ColumnsType<WecomTenantBadCase> = useMemo(
    () => [
      {
        title: t("wecomTenants.caseId"),
        dataIndex: "case_id",
        key: "case_id",
        width: 180,
      },
      {
        title: t("wecomTenants.category"),
        dataIndex: "category",
        key: "category",
        width: 140,
        render: (v: string, row) => (
          <Select
            size="small"
            value={v}
            onChange={(val) =>
              updateBadCase(row.case_id, {
                category: val as BadCaseUpdateRequest["category"],
              })
            }
            style={{ width: 120 }}
            options={(
              Object.keys(CATEGORY_COLORS) as Array<
                keyof typeof CATEGORY_COLORS
              >
            ).map((k) => ({
              label: t(`wecomTenants.${CATEGORY_I18N[k]}`),
              value: k,
            }))}
          />
        ),
      },
      {
        title: t("wecomTenants.status"),
        dataIndex: "status",
        key: "status",
        width: 120,
        render: (v: string, row) => (
          <Select
            size="small"
            value={v}
            onChange={(val) =>
              updateBadCase(row.case_id, {
                status: val as BadCaseUpdateRequest["status"],
              })
            }
            style={{ width: 100 }}
            options={(
              Object.keys(STATUS_COLORS) as Array<keyof typeof STATUS_COLORS>
            ).map((k) => ({
              label: t(`wecomTenants.bc_${k}`),
              value: k,
            }))}
          />
        ),
      },
      {
        title: t("wecomTenants.owner"),
        dataIndex: "owner",
        key: "owner",
        width: 100,
      },
      { title: t("wecomTenants.note"), dataIndex: "note", key: "note" },
      {
        title: t("wecomTenants.updatedAt"),
        dataIndex: "updated_at",
        key: "updated_at",
        width: 160,
        render: (v: string) => (v ? new Date(v).toLocaleString() : "-"),
      },
    ],
    [t, updateBadCase],
  );

  return (
    <Card title={t("wecomTenants.badCases")} bodyStyle={{ padding: 0 }}>
      <Table
        columns={columns}
        dataSource={visibleCases}
        rowKey="case_id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        size="small"
      />
    </Card>
  );
}
