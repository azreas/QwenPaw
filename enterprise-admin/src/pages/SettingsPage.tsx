import { useEffect, useMemo, useState } from "react"
import { Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, Row, Select, Space, Spin, Statistic, Table, Tag, Typography, message } from "antd"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"
import {
  exportComplianceAudit,
  getPlatformSettingsSummary,
} from "@/api/settings"
import type { ComplianceExportRequest, PlatformSettingsSummary } from "@/api/types"

const { Text, Title } = Typography

const formatOptions = [
  { label: "JSON", value: "json" },
  { label: "CSV", value: "csv" },
]

type ExportFormValues = {
  tenant_id?: string
  event_type?: string
  time_range?: [string, string]
  limit?: number
  format?: "json" | "csv"
}

function normalizeExportPayload(values: ExportFormValues): ComplianceExportRequest {
  const payload: ComplianceExportRequest = {
    format: values.format ?? "json",
    limit: values.limit ?? 1000,
    tenant_id: values.tenant_id?.trim() || undefined,
    event_type: values.event_type?.trim() || undefined,
  }
  if (values.time_range && values.time_range.length === 2) {
    payload.start_time = values.time_range[0]
    payload.end_time = values.time_range[1]
  }
  return payload
}

export default function SettingsPage() {
  const [summary, setSummary] = useState<PlatformSettingsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)
  const [form] = Form.useForm<ExportFormValues>()

  useEffect(() => {
    let alive = true
    setLoading(true)
    getPlatformSettingsSummary()
      .then((data) => {
        if (!alive) return
        setSummary(data)
        setError(null)
      })
      .catch((err: Error) => {
        if (!alive) return
        setError(err.message || "设置摘要不可用")
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  const switchRows = useMemo(
    () => summary?.controlled_switches ?? [],
    [summary],
  )

  const handleExport = async (values: ExportFormValues) => {
    setExporting(true)
    try {
      const { blob, filename } = await exportComplianceAudit(normalizeExportPayload(values))
      // Trigger browser download
      try {
        const url = URL.createObjectURL(blob)
        const link = document.createElement("a")
        link.href = url
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      } catch (downloadError) {
        // Fallback for environments where download doesn't work (e.g. JSDOM)
        console.warn("Download trigger failed, blob received:", downloadError)
      }
      message.success(`审计导出已下载: ${filename}`)
    } catch (err) {
      const apiError = err as Error
      message.error(apiError.message || "审计导出失败")
    } finally {
      setExporting(false)
    }
  }

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div>
        <Title level={2}>系统设置</Title>
        <Text type="secondary">平台级只读设置摘要与合规导出</Text>
      </div>

      <PageCompletenessPanel pageKey="settings" compact />

      {loading ? (
        <Card>
          <Spin /> <Text>加载系统设置摘要...</Text>
        </Card>
      ) : null}

      {error ? (
        <Alert
          type="error"
          message="设置摘要不可用"
          description="请稍后重试或查看诊断中心确认后端 readiness 与权限状态。"
          showIcon
        />
      ) : null}

      {summary ? (
        <>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={6}>
              <Card>
                <Statistic title="默认管理入口" value={summary.frontend.root_entry} />
              </Card>
            </Col>
            <Col xs={24} md={6}>
              <Card>
                <Statistic title="Console 状态" value={summary.frontend.console_access} />
              </Card>
            </Col>
            <Col xs={24} md={6}>
              <Card>
                <Statistic title="存储后端" value={summary.storage.backend} />
              </Card>
            </Col>
            <Col xs={24} md={6}>
              <Card>
                <Statistic
                  title="合规导出"
                  value={summary.compliance.export_available ? "available" : "degraded"}
                />
              </Card>
            </Col>
          </Row>

          <Alert
            type="info"
            message="在线修改不在本期范围"
            description="默认入口、Console 开关、环境变量和受控开关仅展示当前状态；如需修改，请走部署变更或后续独立 OpenSpec change。"
            showIcon
          />

          <Card title="受控开关状态">
            <Table
              rowKey="key"
              pagination={false}
              dataSource={switchRows}
              columns={[
                { title: "设置项", dataIndex: "label" },
                { title: "当前状态", dataIndex: "status" },
                { title: "来源", dataIndex: "source" },
                {
                  title: "在线修改",
                  render: (_, row) => (
                    <Tag color={row.online_edit_supported ? "green" : "orange"}>
                      {row.online_edit_supported ? "支持" : "不支持"}
                    </Tag>
                  ),
                },
              ]}
            />
          </Card>

          <Card title="合规审计导出">
            {!summary.compliance.export_available ? (
              <Alert
                type="warning"
                message="合规导出不可用"
                description={summary.compliance.reason || "审计存储不可用"}
                showIcon
                style={{ marginBottom: 16 }}
              />
            ) : null}
            <Text type="secondary">租户字段仅作为审计导出筛选，不会修改租户配置。</Text>
            <Form
              form={form}
              layout="vertical"
              initialValues={{ format: "json", limit: 1000 }}
              onFinish={handleExport}
              style={{ marginTop: 16 }}
            >
              <Row gutter={12}>
                <Col xs={24} md={6}>
                  <Form.Item label="租户筛选" name="tenant_id">
                    <Input placeholder="wx_acme" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="事件类型" name="event_type">
                    <Input placeholder="compliance.exported" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="时间范围" name="time_range">
                    <DatePicker.RangePicker
                      showTime
                      style={{ width: "100%" }}
                      placeholder={["开始时间", "结束时间"]}
                    />
                  </Form.Item>
                </Col>
                <Col xs={12} md={5}>
                  <Form.Item label="格式" name="format">
                    <Select options={formatOptions} />
                  </Form.Item>
                </Col>
                <Col xs={12} md={5}>
                  <Form.Item label="数量上限" name="limit">
                    <InputNumber min={1} max={10000} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={4}>
                  <Form.Item label=" ">
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={exporting}
                      disabled={!summary.compliance.export_available}
                    >
                      导出审计
                    </Button>
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </Card>
        </>
      ) : null}
    </Space>
  )
}
