import { Button, Dropdown } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { CopyOutlined, MoreOutlined, PauseCircleOutlined, PlayCircleOutlined } from "@ant-design/icons";
import type {
  WecomTenantHealthResponse,
  WecomTenantOperationResult,
  WecomTenantSummary,
} from "../../../../../api/types";
import type { TenantRuntimeAction } from "../../hooks/useWecomTenants";
import { TenantHealthTag, TenantRuntimeTag } from "../TenantStatusTag";

type Translate = (key: string, options?: Record<string, unknown>) => string;

interface TenantColumnOptions {
  t: Translate;
  styles: Record<string, string>;
  healthMap: Record<string, WecomTenantHealthResponse>;
  onAction: (agentId: string, action: TenantRuntimeAction) => Promise<void>;
  onCopyPath: (value: string, event: React.MouseEvent) => Promise<void>;
}

function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function createBatchResultColumns(
  t: Translate,
): ColumnsType<WecomTenantOperationResult> {
  return [
    {
      title: "agent_id",
      dataIndex: "agent_id",
      key: "agent_id",
      render: (value: string) => <code>{value}</code>,
    },
    {
      title: t("wecomTenants.batchResultStatus"),
      dataIndex: "success",
      key: "success",
      width: 120,
      render: (success: boolean) =>
        success
          ? t("wecomTenants.batchResultSuccess")
          : t("wecomTenants.batchResultFailed"),
    },
    {
      title: t("wecomTenants.batchResultError"),
      dataIndex: "error",
      key: "error",
      render: (error?: string | null) => error || "-",
    },
  ];
}

export function createTenantColumns({
  t,
  styles,
  healthMap,
  onAction,
  onCopyPath,
}: TenantColumnOptions): ColumnsType<WecomTenantSummary> {
  return [
    {
      title: t("wecomTenants.tenant"),
      dataIndex: "agent_id",
      key: "agent_id",
      width: 220,
      render: (_, tenant) => (
        <div className={styles.tenantIdentity}>
          <strong>{tenant.agent_id}</strong>
          <span>{tenant.tenant_id}</span>
        </div>
      ),
    },
    {
      title: t("wecomTenants.status"),
      key: "status",
      width: 150,
      render: (_, tenant) => (
        <div className={styles.statusStack}>
          <TenantRuntimeTag tenant={tenant} />
          <TenantHealthTag tenant={tenant} health={healthMap[tenant.agent_id]} />
        </div>
      ),
    },
    {
      title: t("wecomTenants.activity"),
      key: "activity",
      width: 120,
      render: (_, tenant) => (
        <span className={styles.mutedText}>
          {tenant.chat_count} / {tenant.job_count}
        </span>
      ),
    },
    {
      title: t("wecomTenants.updatedAt"),
      dataIndex: "updated_at",
      key: "updated_at",
      width: 160,
      render: formatDate,
    },
    {
      title: t("wecomTenants.actions"),
      key: "actions",
      width: 60,
      render: (_, tenant) => (
        <Dropdown
          menu={{
            items: [
              {
                key: "start",
                label: t("wecomTenants.start"),
                icon: <PlayCircleOutlined />,
                disabled: tenant.running || !tenant.exists,
              },
              {
                key: "stop",
                label: t("wecomTenants.stop"),
                icon: <PauseCircleOutlined />,
                disabled: !tenant.running,
              },
              {
                key: "copyPath",
                label: t("wecomTenants.copyWorkspacePath"),
                icon: <CopyOutlined />,
              },
            ],
            onClick: ({ key, domEvent }: { key: string; domEvent: React.MouseEvent }) => {
              domEvent.stopPropagation();
              if (key === "start") onAction(tenant.agent_id, "start");
              else if (key === "stop") onAction(tenant.agent_id, "stop");
              else if (key === "copyPath") onCopyPath(tenant.workspace_dir, domEvent);
            },
          }}
          trigger={["click"]}
        >
          <Button
            size="small"
            icon={<MoreOutlined />}
            aria-label={t("wecomTenants.moreActions")}
            onClick={(e) => e.stopPropagation()}
          />
        </Dropdown>
      ),
    },
  ];
}
