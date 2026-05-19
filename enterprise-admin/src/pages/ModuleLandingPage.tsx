import React from "react"
import { Result, Button, Card, Space, Tag, Typography } from "antd"
import { useNavigate } from "react-router-dom"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"
import type { EnterprisePageKey } from "@/features/platform-readiness/pageCompletenessModel"

const { Paragraph, Text } = Typography

interface ModuleLandingPageProps {
  title?: string
  description?: string
  status?: "info" | "success" | "warning" | "error" | "404" | "403" | "500"
  badge?: string
  phase?: string
  currentAlternatives?: string[]
  completenessKey?: EnterprisePageKey
}

const ModuleLandingPage: React.FC<ModuleLandingPageProps> = ({
  title = "模块建设中",
  description = "该功能模块正在开发中，敬请期待...",
  status = "info",
  badge,
  phase,
  currentAlternatives,
  completenessKey,
}) => {
  const navigate = useNavigate()

  const iconMap: Record<string, React.ReactNode> = {
    info: "🚧",
    success: "✅",
    warning: "⚠️",
    error: "❌",
    "404": "🔍",
    "403": "🔒",
    "500": "⚡",
  }

  return (
    <div
      style={{
        minHeight: "calc(100vh - 64px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <Card style={{ width: "100%", maxWidth: 640, textAlign: "center" }}>
        <Result
          icon={<span style={{ fontSize: 72 }}>{iconMap[status] || "🚧"}</span>}
          title={
            <Space direction="vertical" size={8}>
              <Space size={8} wrap>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {title}
                </Typography.Title>
                {badge && <Tag color="default">{badge}</Tag>}
              </Space>
              {phase && <Text type="secondary">{phase}</Text>}
            </Space>
          }
          subTitle={description}
          extra={
            <Space direction="vertical" size={16} style={{ width: "100%" }}>
              {currentAlternatives && currentAlternatives.length > 0 && (
                <div style={{ textAlign: "left" }}>
                  <Text strong>当前可用入口</Text>
                  <div style={{ marginTop: 8 }}>
                    {currentAlternatives.map((item) => (
                      <Paragraph key={item} style={{ marginBottom: 6 }}>
                        {item}
                      </Paragraph>
                    ))}
                  </div>
                </div>
              )}
              {completenessKey && (
                <div style={{ textAlign: "left" }}>
                  <PageCompletenessPanel pageKey={completenessKey} compact />
                </div>
              )}
              <Button type="primary" onClick={() => navigate("/dashboard")}>
                返回首页
              </Button>
            </Space>
          }
        />
      </Card>
    </div>
  )
}

export default ModuleLandingPage
