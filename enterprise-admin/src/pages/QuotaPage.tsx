import React, { useEffect, useMemo, useState } from "react"
import { Alert, Card, Col, Row, Space, Statistic, Table, Tag, Typography, message } from "antd"
import {
  getQuotaConfigSummary,
  getTokenUsageDetails,
  getTokenUsageSummary,
  listQuotaAuditEvents,
} from "@/api/quota"
import type {
  AuditEventItem,
  QuotaConfigSummary,
  TokenUsageRecord,
  TokenUsageSummary,
} from "@/api/types"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

interface ModelUsageRow {
  key: string
  provider_id: string
  model: string
  agent_id: string
  prompt_tokens: number
  completion_tokens: number
  call_count: number
}

function aggregateModelUsage(records: TokenUsageRecord[]): ModelUsageRow[] {
  const byKey = new Map<string, ModelUsageRow>()
  for (const record of records) {
    const key = `${record.provider_id}:${record.model}:${record.agent_id || "-"}`
    const current = byKey.get(key) ?? {
      key,
      provider_id: record.provider_id || "-",
      model: record.model || "-",
      agent_id: record.agent_id || "-",
      prompt_tokens: 0,
      completion_tokens: 0,
      call_count: 0,
    }
    current.prompt_tokens += record.prompt_tokens
    current.completion_tokens += record.completion_tokens
    current.call_count += record.call_count
    byKey.set(key, current)
  }
  return Array.from(byKey.values()).sort(
    (a, b) =>
      b.prompt_tokens + b.completion_tokens - (a.prompt_tokens + a.completion_tokens),
  )
}

const QuotaPage: React.FC = () => {
  const [summary, setSummary] = useState<TokenUsageSummary | null>(null)
  const [details, setDetails] = useState<TokenUsageRecord[]>([])
  const [quota, setQuota] = useState<QuotaConfigSummary | null>(null)
  const [quotaEvents, setQuotaEvents] = useState<AuditEventItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getTokenUsageSummary(),
      getTokenUsageDetails(),
      getQuotaConfigSummary(),
      listQuotaAuditEvents(),
    ])
      .then(([summaryResp, detailsResp, quotaResp, auditResp]) => {
        setSummary(summaryResp)
        setDetails(detailsResp)
        setQuota(quotaResp)
        setQuotaEvents(auditResp.events)
      })
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : "加载配额用量失败")
      })
      .finally(() => setLoading(false))
  }, [])

  const modelUsage = useMemo(() => aggregateModelUsage(details), [details])
  const dateUsage = useMemo(
    () =>
      Object.entries(summary?.by_date || {}).map(([date, value]) => ({
        key: date,
        date,
        ...value,
      })),
    [summary],
  )

  return (
    <div className="enterprise-page">
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            配额管理
          </Title>
          <Text type="secondary">Token 用量、默认限额和超限审计只读视图</Text>
        </div>

        <PageCompletenessPanel pageKey="quota" compact />

        <Alert
          type="info"
          showIcon
          message="受控写入阶段化开放"
          description="当前页面先产品化 Token Usage、默认限额和 quota.denied 审计视图；配额调整、超限处置和告警策略仍需后端写契约与审计闭环后开放。"
        />

        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card loading={loading}>
              <Statistic
                title="Prompt Tokens"
                value={summary?.total_prompt_tokens ?? 0}
              />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card loading={loading}>
              <Statistic
                title="Completion Tokens"
                value={summary?.total_completion_tokens ?? 0}
              />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card loading={loading}>
              <Statistic title="调用次数" value={summary?.total_calls ?? 0} />
            </Card>
          </Col>
        </Row>

        <Card title="默认配额策略" loading={loading}>
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Space wrap>
              <Tag color={quota?.enabled ? "green" : "default"}>
                {quota?.enabled ? "已启用" : "未启用"}
              </Tag>
              <Tag color={quota?.redis_url_set ? "blue" : "orange"}>
                {quota?.redis_url_set ? "Redis 已配置" : "Redis 未配置"}
              </Tag>
            </Space>
            <Table
              rowKey={(record) => `${record.dimension}:${record.resource}`}
              size="small"
              pagination={false}
              dataSource={quota?.default_limits || []}
              columns={[
                { title: "维度", dataIndex: "dimension" },
                { title: "窗口", dataIndex: "window" },
                { title: "资源", dataIndex: "resource" },
                { title: "上限", dataIndex: "max_value" },
              ]}
            />
          </Space>
        </Card>

        <Card title="模型与租户用量" loading={loading}>
          <Table
            rowKey="key"
            size="small"
            dataSource={modelUsage}
            pagination={{ pageSize: 8 }}
            columns={[
              { title: "Provider", dataIndex: "provider_id" },
              { title: "Model", dataIndex: "model" },
              { title: "Agent", dataIndex: "agent_id" },
              { title: "Prompt", dataIndex: "prompt_tokens" },
              { title: "Completion", dataIndex: "completion_tokens" },
              { title: "Calls", dataIndex: "call_count" },
            ]}
          />
        </Card>

        <Card title="按日趋势" loading={loading}>
          <Table
            rowKey="date"
            size="small"
            dataSource={dateUsage}
            pagination={false}
            columns={[
              { title: "日期", dataIndex: "date" },
              { title: "Prompt", dataIndex: "prompt_tokens" },
              { title: "Completion", dataIndex: "completion_tokens" },
              { title: "Calls", dataIndex: "call_count" },
            ]}
          />
        </Card>

        <Card title="超限审计" loading={loading}>
          <Table
            rowKey="id"
            size="small"
            dataSource={quotaEvents}
            pagination={{ pageSize: 6 }}
            columns={[
              { title: "事件", dataIndex: "event_type" },
              { title: "结果", dataIndex: "outcome" },
              { title: "租户", dataIndex: "tenant_id" },
              { title: "资源", dataIndex: "resource_id" },
              { title: "时间", dataIndex: "created_at" },
            ]}
          />
        </Card>
      </Space>
    </div>
  )
}

export default QuotaPage
