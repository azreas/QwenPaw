import React, { useEffect, useState } from "react"
import {
  Row,
  Col,
  Card,
  Statistic,
  Progress,
  Tag,
  List,
  Spin,
  Alert,
  Space,
  Typography,
  Divider,
} from "antd"
import {
  CheckCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  ApiOutlined,
  SecurityScanOutlined,
} from "@ant-design/icons"
import {
  fetchDashboardData,
  calculateHealthScore,
  countEnabledFeatures,
  getHealthStatusText,
  getReadinessStatusText,
  formatVersion,
  getEnterpriseFeaturesList,
  getReadyComponentsList,
} from "@/features/dashboard/dashboardModel"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"
import type { DashboardData } from "@/features/dashboard/dashboardModel"

const { Title, Text } = Typography

const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        setError(null)
        const dashboardData = await fetchDashboardData()
        setData(dashboardData)
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载数据失败")
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "60vh",
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
        />
      </div>
    )
  }

  if (!data) {
    return null
  }

  const healthScore = calculateHealthScore(data.readyStatus)
  const healthInfo = getHealthStatusText(healthScore)
  const enabledFeaturesCount = countEnabledFeatures(data.enterpriseReadiness)
  const readinessInfo = getReadinessStatusText(data.enterpriseReadiness.status)
  const featuresList = getEnterpriseFeaturesList(data.enterpriseReadiness)
  const readyComponents = getReadyComponentsList(data.readyStatus)

  const healthIcon =
    healthInfo.status === "healthy" ? (
      <CheckCircleOutlined style={{ color: "#52c41a", fontSize: 32 }} />
    ) : healthInfo.status === "warning" ? (
      <WarningOutlined style={{ color: "#faad14", fontSize: 32 }} />
    ) : (
      <ClockCircleOutlined style={{ color: "#ff4d4f", fontSize: 32 }} />
    )

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        运营总览
      </Title>

      <div style={{ marginBottom: 24 }}>
        <PageCompletenessPanel pageKey="dashboard" compact />
      </div>

      <Row gutter={[16, 16]}>
        {/* 系统健康状态 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="系统健康度"
              value={healthScore}
              suffix="%"
              prefix={healthIcon}
              valueStyle={{
                color:
                  healthInfo.status === "healthy"
                    ? "#52c41a"
                    : healthInfo.status === "warning"
                    ? "#faad14"
                    : "#ff4d4f",
              }}
            />
            <Progress
              percent={healthScore}
              status={
                healthInfo.status === "healthy"
                  ? "success"
                  : healthInfo.status === "warning"
                  ? "normal"
                  : "exception"
              }
            />
          </Card>
        </Col>

        {/* 版本信息 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="系统版本"
              value={formatVersion(data.versionInfo)}
              prefix={<ApiOutlined style={{ color: "#1890ff" }} />}
              valueStyle={{ fontSize: 18 }}
            />
            {data.versionInfo.buildTime && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                构建时间: {new Date(data.versionInfo.buildTime).toLocaleString()}
              </Text>
            )}
          </Card>
        </Col>

        {/* 企业就绪状态 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="企业就绪状态"
              value={readinessInfo.label}
              prefix={<DatabaseOutlined style={{ color: "#722ed1" }} />}
              valueStyle={{ fontSize: 18 }}
            />
            <Tag color={readinessInfo.type === "success" ? "green" : readinessInfo.type === "warning" ? "orange" : "red"}>
              {readinessInfo.label}
            </Tag>
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">存储后端: {data.enterpriseReadiness.storageBackend || "-"}</Text>
            </div>
          </Card>
        </Col>

        {/* 企业功能启用情况 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="企业功能启用"
              value={enabledFeaturesCount}
              suffix={`/ ${featuresList.length}`}
              prefix={<SecurityScanOutlined style={{ color: "#eb2f96" }} />}
            />
            <Progress
              percent={Math.round((enabledFeaturesCount / featuresList.length) * 100)}
              strokeColor="#eb2f96"
            />
          </Card>
        </Col>
      </Row>

      {data.opsOverview && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="租户总数"
                value={data.opsOverview.total_tenants}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="运行租户"
                value={data.opsOverview.running_tenants}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="异常租户"
                value={data.opsOverview.unhealthy_tenants}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="24h 调用"
                value={data.opsOverview.business_calls_24h}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="失败调用"
                value={data.opsOverview.failed_calls_24h}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="失败率"
                value={Math.round(data.opsOverview.failure_rate * 1000) / 10}
                suffix="%"
              />
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {/* 系统检查状态 */}
        <Col xs={24} lg={12}>
          <Card title="系统组件状态">
            <List
              dataSource={readyComponents}
              locale={{ emptyText: "暂无组件状态" }}
              renderItem={(item) => (
                <List.Item>
                  <Space>
                    {item.status === "ok" ? (
                      <CheckCircleOutlined style={{ color: "#52c41a" }} />
                    ) : item.status === "degraded" ? (
                      <WarningOutlined style={{ color: "#faad14" }} />
                    ) : (
                      <WarningOutlined style={{ color: "#ff4d4f" }} />
                    )}
                    <Space direction="vertical" size={0}>
                      <span>{item.name}</span>
                      {item.summary && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {item.summary}
                        </Text>
                      )}
                    </Space>
                  </Space>
                  <Tag
                    color={
                      item.status === "ok"
                        ? "green"
                        : item.status === "degraded"
                        ? "orange"
                        : "red"
                    }
                  >
                    {item.status === "ok"
                      ? "正常"
                      : item.status === "degraded"
                      ? "降级"
                      : "异常"}
                  </Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* 企业功能列表 */}
        <Col xs={24} lg={12}>
          <Card title="企业功能状态">
            <List
              grid={{ gutter: 8, column: 2 }}
              dataSource={featuresList}
              renderItem={(feature) => (
                <List.Item>
                  <Card size="small" style={{ textAlign: "center" }}>
                    <div style={{ marginBottom: 8 }}>
                      <Tag color={feature.enabled ? "green" : "default"}>
                        {feature.enabled ? "已启用" : "未启用"}
                      </Tag>
                    </div>
                    <Text strong>{feature.name}</Text>
                  </Card>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* API 状态卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="认证状态">
            <List>
              <List.Item>
                <Space>
                  {data.authStatus.authenticated || data.authStatus.authDisabled ? (
                    <CheckCircleOutlined style={{ color: "#52c41a" }} />
                  ) : (
                    <WarningOutlined style={{ color: "#faad14" }} />
                  )}
                  <span>认证状态</span>
                </Space>
                <Tag color={data.authStatus.authenticated || data.authStatus.authDisabled ? "green" : "orange"}>
                  {data.authStatus.authDisabled
                    ? "认证未启用 / 已放行"
                    : data.authStatus.authenticated
                    ? "已认证"
                    : "未认证"}
                </Tag>
              </List.Item>
              {data.authStatus.username && (
                <List.Item>
                  <span>当前用户</span>
                  <Text strong>{data.authStatus.username}</Text>
                </List.Item>
              )}
              {data.authStatus.role && (
                <List.Item>
                  <span>用户角色</span>
                  <Text strong>{data.authStatus.role}</Text>
                </List.Item>
              )}
            </List>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="后端接口状态">
            <List>
              <List.Item>
                <Space>
                  <ApiOutlined style={{ color: "#1890ff" }} />
                  <span>/api/auth/status</span>
                </Space>
                <Tag color="green">正常</Tag>
              </List.Item>
              <List.Item>
                <Space>
                  <ApiOutlined style={{ color: "#1890ff" }} />
                  <span>/api/version</span>
                </Space>
                <Tag color="green">正常</Tag>
              </List.Item>
              <List.Item>
                <Space>
                  <ApiOutlined style={{ color: "#1890ff" }} />
                  <span>/ready</span>
                </Space>
                <Tag color={data.readyStatus.ready ? "green" : "orange"}>
                  {data.readyStatus.ready ? "就绪" : "未就绪"}
                </Tag>
              </List.Item>
              <List.Item>
                <Space>
                  <ApiOutlined style={{ color: "#1890ff" }} />
                  <span>/api/enterprise/readiness</span>
                </Space>
                <Tag
                  color={
                    data.enterpriseReadiness.status === "ready" ? "green" : "orange"
                  }
                >
                  {data.enterpriseReadiness.status === "ready" ? "就绪" : "未就绪"}
                </Tag>
              </List.Item>
            </List>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage
