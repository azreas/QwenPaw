import React, { useEffect, useState } from "react"
import {
  Alert,
  Card,
  Col,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd"
import { getRawMetrics, parsePrometheusMetrics } from "@/api/metrics"
import type { MetricsSummary } from "@/api/types"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

function formatMetricValue(value?: number): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-"
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(4)
}

const MetricsPage: React.FC = () => {
  const [summary, setSummary] = useState<MetricsSummary | null>(null)
  const [loadError, setLoadError] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getRawMetrics()
      .then((raw) => {
        setLoadError("")
        setSummary(parsePrometheusMetrics(raw))
      })
      .catch((err: unknown) => {
        const errorMessage = err instanceof Error ? err.message : "加载指标摘要失败"
        setLoadError(errorMessage)
        setSummary(null)
        message.error(errorMessage)
      })
      .finally(() => setLoading(false))
  }, [])

  const metrics = summary?.metrics ?? []
  const showUnavailable = Boolean(summary?.unavailable)
  const showEmptyState =
    !showUnavailable && (summary?.sampleCount ?? 0) === 0 && Boolean(summary)

  return (
    <div className="enterprise-page">
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            指标监控
          </Title>
          <Text type="secondary">Prometheus 指标只读摘要和原始预览</Text>
        </div>

        <PageCompletenessPanel pageKey="metrics" compact />

        <Alert
          type="info"
          showIcon
          message="告警/趋势/导出/跨租户下钻阶段化开放"
          description="当前页面只提供 Prometheus 原始指标的只读摘要与文本预览，告警配置、趋势分析、导出能力和跨租户下钻仍按后续阶段逐步开放。"
        />

        {loadError ? (
          <Alert
            type="error"
            showIcon
            message="加载指标监控失败"
            description={loadError}
          />
        ) : null}

        {showUnavailable ? (
          <Alert
            type="info"
            showIcon
            message="Observability 未启用"
            description="当前环境未启用指标观测服务，/api/metrics 返回了只读占位说明。"
          />
        ) : null}

        {showEmptyState ? (
          <Alert
            type="info"
            showIcon
            message="暂无可用指标"
            description="当前未解析到 Prometheus 样本，可先检查 observability registry 或指标采集状态。"
          />
        ) : null}

        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Statistic title="指标名称数" value={summary?.metricCount ?? 0} />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Statistic title="样本数" value={summary?.sampleCount ?? 0} />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Statistic title="活跃序列数" value={summary?.seriesCount ?? 0} />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Statistic title="指标类型数" value={summary?.typeCount ?? 0} />
            </Card>
          </Col>
        </Row>

        <Card title="指标表" loading={loading}>
          <Table
            rowKey="name"
            size="small"
            dataSource={metrics}
            pagination={{ pageSize: 8, hideOnSinglePage: true }}
            locale={{ emptyText: "暂无指标摘要" }}
            columns={[
              {
                title: "指标名",
                dataIndex: "name",
                width: 240,
              },
              {
                title: "类型",
                dataIndex: "type",
                width: 120,
                render: (value: string) => <Tag>{value}</Tag>,
              },
              {
                title: "样本数",
                dataIndex: "sampleCount",
                width: 100,
              },
              {
                title: "最新值",
                dataIndex: "latestValue",
                width: 120,
                render: (value?: number) => formatMetricValue(value),
              },
              {
                title: "HELP 说明",
                dataIndex: "help",
                render: (value: string) => value || "-",
              },
            ]}
          />
        </Card>

        <Card title="原始文本预览" loading={loading}>
          <pre
            style={{
              margin: 0,
              maxHeight: 320,
              overflow: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {summary?.raw ?? ""}
          </pre>
        </Card>
      </Space>
    </div>
  )
}

export default MetricsPage
