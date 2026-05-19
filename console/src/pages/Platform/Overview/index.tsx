import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Button,
  Card,
  Col,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { PageHeader } from "@/components/PageHeader";
import { platformTenancyApi } from "../../../api/modules/platformTenancy";
import type {
  TenantPolicy,
  TenantRecord,
  TenantTemplate,
} from "../../../api/types/platformTenancy";
import { useAppMessage } from "../../../hooks/useAppMessage";

function isRunningTenant(tenant: TenantRecord): boolean {
  const status = tenant.status.toLowerCase();
  return status === "running" || status === "active";
}

function statusColor(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "running" || normalized === "active") return "green";
  if (normalized === "stopped" || normalized === "disabled") return "default";
  if (normalized === "error" || normalized === "failed") return "red";
  return "blue";
}

function formatTime(value: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function PlatformOverviewPage() {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [tenants, setTenants] = useState<TenantRecord[]>([]);
  const [policies, setPolicies] = useState<TenantPolicy[]>([]);
  const [templates, setTemplates] = useState<TenantTemplate[]>([]);
  const [loading, setLoading] = useState(false);

  const loadOverview = async () => {
    setLoading(true);
    try {
      const [tenantResponse, policyResponse, templateResponse] =
        await Promise.all([
          platformTenancyApi.listTenants(),
          platformTenancyApi.listPolicies(),
          platformTenancyApi.listTemplates(),
        ]);
      setTenants(tenantResponse.tenants);
      setPolicies(policyResponse.policies);
      setTemplates(templateResponse.templates);
    } catch (error) {
      console.error("Failed to load platform tenants:", error);
      message.error(t("platformOverview.loadFailed", "加载平台租户失败"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadOverview();
  }, []);

  const runningTenants = useMemo(
    () => tenants.filter(isRunningTenant).length,
    [tenants],
  );

  const columns: TableColumnsType<TenantRecord> = [
    {
      title: t("platformOverview.table.tenant", "租户"),
      dataIndex: "display_name",
      render: (value: string, tenant) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{value || tenant.tenant_id}</Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {tenant.tenant_id}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: t("platformOverview.table.agent", "Agent"),
      dataIndex: "agent_id",
      render: (value: string) => <Typography.Text code>{value}</Typography.Text>,
    },
    {
      title: t("platformOverview.table.status", "状态"),
      dataIndex: "status",
      render: (value: string) => <Tag color={statusColor(value)}>{value}</Tag>,
    },
    {
      title: t("platformOverview.table.policy", "策略"),
      dataIndex: "policy_id",
      render: (value: string) => value || "-",
    },
    {
      title: t("platformOverview.table.template", "模板"),
      dataIndex: "template_id",
      render: (value: string) => value || "-",
    },
    {
      title: t("platformOverview.table.source", "来源"),
      dataIndex: "source",
      render: (value: string) => value || "-",
    },
    {
      title: t("platformOverview.table.updatedAt", "更新时间"),
      dataIndex: "updated_at",
      render: formatTime,
    },
  ];

  return (
    <div>
      <PageHeader
        parent={t("nav.platformOps")}
        current={t("nav.platformOverview")}
        subRow={
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            {t(
              "platformOverview.subtitle",
              "汇总多租户运行态、策略和模板的整体情况，便于快速巡检。",
            )}
          </Typography.Text>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
              onClick={loadOverview}
              loading={loading}
            >
            {t("common.refresh", "刷新")}
          </Button>
        }
      />

      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={t("platformOverview.totalTenants", "租户总数")}
                value={tenants.length}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={t("platformOverview.runningTenants", "运行租户")}
                value={runningTenants}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={t("platformOverview.policyCount", "策略数")}
                value={policies.length}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={t("platformOverview.templateCount", "模板数")}
                value={templates.length}
              />
            </Card>
          </Col>
        </Row>

        <Card
          title={t("platformOverview.table.title", "租户概览")}
          styles={{ body: { padding: 0 } }}
        >
          <Table<TenantRecord>
            rowKey="tenant_id"
            columns={columns}
            dataSource={tenants}
            loading={loading}
            pagination={{ pageSize: 10, showSizeChanger: true }}
          />
        </Card>
      </Space>
    </div>
  );
}
