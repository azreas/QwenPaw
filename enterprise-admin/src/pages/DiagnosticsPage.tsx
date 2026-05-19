import React, { useEffect, useState } from "react"
import { Alert, Card, Descriptions, Select, Space, Table, Tag, Typography, message } from "antd"
import {
  getDiagnosticsOverview,
  getTenantDiagnosticsSnapshot,
} from "@/api/diagnostics"
import { listWecomTenants } from "@/api/tenants"
import type {
  DiagnosticsOverview,
  TenantDiagnosticsSnapshot,
} from "@/api/diagnostics"
import type { ReadyComponent, WecomTenantSummary } from "@/api/types"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

function statusColor(status?: string | boolean): string {
  if (status === true || status === "ok" || status === "pass" || status === "healthy" || status === "ready") {
    return "green"
  }
  if (status === "warn" || status === "degraded") {
    return "orange"
  }
  return "red"
}

function normalizeEnterpriseCheckStatus(record: {
  status?: string
  message?: string
}): string {
  if (
    record.status === "pass" &&
    record.message?.toLowerCase().includes("unavailable")
  ) {
    return "fail"
  }
  return record.status || "unknown"
}

const DiagnosticsPage: React.FC = () => {
  const [overview, setOverview] = useState<DiagnosticsOverview | null>(null)
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string>()
  const [tenantSnapshot, setTenantSnapshot] =
    useState<TenantDiagnosticsSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [tenantLoading, setTenantLoading] = useState(false)

  useEffect(() => {
    Promise.all([getDiagnosticsOverview(), listWecomTenants()])
      .then(([overviewResp, tenantsResp]) => {
        setOverview(overviewResp)
        setTenants(tenantsResp.tenants)
        setSelectedAgentId(tenantsResp.tenants[0]?.agent_id)
      })
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : "加载诊断中心失败")
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedAgentId) return
    setTenantLoading(true)
    getTenantDiagnosticsSnapshot(selectedAgentId)
      .then(setTenantSnapshot)
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : "加载租户诊断失败")
      })
      .finally(() => setTenantLoading(false))
  }, [selectedAgentId])

  const readyComponents: ReadyComponent[] = overview?.ready.components || []
  const enterpriseChecks = Array.isArray(overview?.enterprise.checks)
    ? overview?.enterprise.checks
    : []

  return (
    <div className="enterprise-page">
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Space
          align="start"
          style={{ width: "100%", justifyContent: "space-between" }}
        >
          <div>
            <Title level={3} style={{ margin: 0 }}>
              诊断中心
            </Title>
            <Text type="secondary">平台 readiness、组件状态和租户配置诊断</Text>
          </div>
          <Space direction="vertical" size={4} style={{ minWidth: 280 }}>
            <Text>租户</Text>
            <Select
              aria-label="诊断租户选择器"
              value={selectedAgentId}
              options={tenants.map((tenant) => ({
                label: `${tenant.tenant_id} / ${tenant.agent_id}`,
                value: tenant.agent_id,
              }))}
              onChange={setSelectedAgentId}
              disabled={tenants.length === 0}
            />
          </Space>
        </Space>

        <PageCompletenessPanel pageKey="diagnostics" compact />

        <Alert
          type="info"
          showIcon
          message="日志摘要与安全测试链接阶段化开放"
          description="当前聚合 /ready、enterprise readiness、租户 health 与入口诊断。日志检索、测试链接触发和跨租户诊断报告仍等待后端契约。"
        />

        <Card title="平台 readiness" loading={loading}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="/ready">
              <Tag color={overview?.ready.ready ? "green" : "orange"}>
                {overview?.ready.ready ? "ready" : "not ready"}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Enterprise">
              <Tag color={statusColor(overview?.enterprise.status)}>
                {overview?.enterprise.status || "-"}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title="组件状态" loading={loading}>
          <Table
            rowKey="name"
            size="small"
            dataSource={readyComponents}
            pagination={false}
            columns={[
              { title: "组件", dataIndex: "name" },
              {
                title: "状态",
                render: (_, record) => (
                  <Tag color={statusColor(record.status ?? record.ready)}>
                    {record.status || String(record.ready)}
                  </Tag>
                ),
              },
              { title: "消息", dataIndex: "message" },
            ]}
          />
        </Card>

        <Card title="企业化检查" loading={loading}>
          <Table
            rowKey="name"
            size="small"
            dataSource={enterpriseChecks as { name: string; status: string; required: boolean; message: string }[]}
            pagination={false}
            columns={[
              { title: "检查项", dataIndex: "name" },
              {
                title: "状态",
                render: (_, record) => {
                  const status = normalizeEnterpriseCheckStatus(record)
                  return <Tag color={statusColor(status)}>{status}</Tag>
                },
              },
              {
                title: "必需",
                render: (_, record) => (record.required ? "是" : "否"),
              },
              { title: "说明", dataIndex: "message" },
            ]}
          />
        </Card>

        <Card title="租户诊断" loading={tenantLoading}>
          {tenantSnapshot ? (
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="健康状态">
                <Tag color={statusColor(tenantSnapshot.health.status)}>
                  {tenantSnapshot.health.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="入口诊断">
                <Tag color={statusColor(tenantSnapshot.entry.status)}>
                  {tenantSnapshot.entry.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Health Checks">
                <pre style={{ margin: 0 }}>
                  {JSON.stringify(tenantSnapshot.health.checks, null, 2)}
                </pre>
              </Descriptions.Item>
              <Descriptions.Item label="Entry Checks">
                <pre style={{ margin: 0 }}>
                  {JSON.stringify(tenantSnapshot.entry.checks, null, 2)}
                </pre>
              </Descriptions.Item>
            </Descriptions>
          ) : (
            <Alert type="info" showIcon message="暂无租户诊断数据" />
          )}
        </Card>
      </Space>
    </div>
  )
}

export default DiagnosticsPage
