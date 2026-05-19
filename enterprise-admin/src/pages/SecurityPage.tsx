import React, { useEffect, useState } from "react"
import { Alert, Button, Card, Form, InputNumber, Space, Table, Tag, Typography, message } from "antd"
import {
  listPermissionDenials,
  listTenantPolicies,
  putTenantPolicy,
} from "@/api/security"
import type { AuditEventItem, TenantPolicy } from "@/api/types"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

const SecurityPage: React.FC = () => {
  const [policies, setPolicies] = useState<TenantPolicy[]>([])
  const [denials, setDenials] = useState<AuditEventItem[]>([])
  const [loading, setLoading] = useState(true)
  const [savingPolicyId, setSavingPolicyId] = useState("")

  const loadSecurityState = async () => {
    try {
      setLoading(true)
      const [policyResp, denialResp] = await Promise.all([
        listTenantPolicies(),
        listPermissionDenials(),
      ])
      setPolicies(policyResp.policies)
      setDenials(denialResp.events)
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载安全中心失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSecurityState()
  }, [])

  const savePolicyQuota = async (
    policy: TenantPolicy,
    values: { token_quota_monthly?: number | null },
  ) => {
    try {
      setSavingPolicyId(policy.policy_id)
      await putTenantPolicy(policy.policy_id, {
        ...policy,
        token_quota_monthly: values.token_quota_monthly ?? null,
      })
      message.success("租户策略已保存")
      await loadSecurityState()
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存租户策略失败")
    } finally {
      setSavingPolicyId("")
    }
  }

  return (
    <div className="enterprise-page">
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            安全中心
          </Title>
          <Text type="secondary">策略基线、权限拒绝审计与安全治理入口</Text>
        </div>

        <PageCompletenessPanel pageKey="security" compact />

        <Alert
          type="info"
          showIcon
          message="安全处置分阶段开放"
          description="当前接入已有审计的租户策略写契约和权限拒绝审计查询；审批处置、blocked history 清理和完整安全策略编排仍在阶段化开放中。"
        />

        <Card title="租户策略基线" loading={loading}>
          <Table
            rowKey="policy_id"
            dataSource={policies}
            pagination={false}
            columns={[
              {
                title: "策略",
                dataIndex: "display_name",
                render: (value: string, record) => (
                  <Space direction="vertical" size={0}>
                    <Text strong>{value}</Text>
                    <Text type="secondary">{record.policy_id}</Text>
                  </Space>
                ),
              },
              {
                title: "能力边界",
                render: (_, record) => (
                  <Space wrap>
                    <Tag color={record.allow_mcp ? "green" : "default"}>MCP</Tag>
                    <Tag color={record.allow_tools ? "green" : "default"}>Tools</Tag>
                    <Tag color={record.allow_tasks ? "green" : "default"}>Tasks</Tag>
                    <Tag color={record.advanced_config_enabled ? "blue" : "default"}>
                      Advanced
                    </Tag>
                  </Space>
                ),
              },
              {
                title: "月 Token 配额",
                render: (_, record) => (
                  <Form
                    layout="inline"
                    initialValues={{
                      token_quota_monthly: record.token_quota_monthly ?? undefined,
                    }}
                    onFinish={(values) => savePolicyQuota(record, values)}
                  >
                    <Form.Item name="token_quota_monthly">
                      <InputNumber
                        min={0}
                        placeholder="未设置"
                        aria-label={`${record.policy_id} 月 Token 配额`}
                      />
                    </Form.Item>
                    <Button
                      htmlType="submit"
                      size="small"
                      loading={savingPolicyId === record.policy_id}
                    >
                      保存
                    </Button>
                  </Form>
                ),
              },
            ]}
          />
        </Card>

        <Card title="权限拒绝审计" loading={loading}>
          <Table
            rowKey="id"
            size="small"
            dataSource={denials}
            pagination={{ pageSize: 8 }}
            columns={[
              { title: "动作", dataIndex: "action" },
              { title: "租户", dataIndex: "tenant_id" },
              { title: "操作者", dataIndex: "actor_id" },
              { title: "资源", dataIndex: "resource_type" },
              { title: "资源 ID", dataIndex: "resource_id" },
              { title: "时间", dataIndex: "created_at" },
            ]}
          />
        </Card>
      </Space>
    </div>
  )
}

export default SecurityPage
