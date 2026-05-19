import { Alert, Card, Col, Row, Space, Tag, Typography } from "antd"
import {
  getPageCompleteness,
  getPageCompletenessStatusTag,
  type EnterprisePageKey,
} from "./pageCompletenessModel"

const { Paragraph, Text } = Typography

interface PageCompletenessPanelProps {
  pageKey: EnterprisePageKey | string
  compact?: boolean
  showInternalDetails?: boolean
}

export default function PageCompletenessPanel({
  pageKey,
  compact = false,
  showInternalDetails = false,
}: PageCompletenessPanelProps) {
  const definition = getPageCompleteness(pageKey)

  if (!showInternalDetails || !definition) {
    return null
  }

  const status = getPageCompletenessStatusTag(definition.status)

  return (
    <Card size="small" title="页面完整性">
      <Space
        direction="vertical"
        size={compact ? 8 : 12}
        style={{ width: "100%" }}
      >
        <Space wrap>
          <Tag color={status.color}>{status.text}</Tag>
          <Text type="secondary">{definition.title}</Text>
        </Space>
        <Paragraph style={{ marginBottom: 0 }}>{definition.positioning}</Paragraph>
        <Alert
          type={definition.status === "staged" ? "warning" : "info"}
          showIcon
          message="完成门槛"
          description={definition.completeWhen}
        />
        <Row gutter={[12, 12]}>
          <Col xs={24} lg={12}>
            <Text strong>当前工作流</Text>
            <ul>
              {definition.currentWorkflow.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Col>
          <Col xs={24} lg={12}>
            <Text strong>主要缺口</Text>
            <ul>
              {definition.gaps.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Col>
        </Row>
        {definition.stagedCapabilities.length > 0 ? (
          <Space wrap>
            <Text strong>阶段化能力</Text>
            {definition.stagedCapabilities.map((item) => (
              <Tag key={item}>{item}</Tag>
            ))}
          </Space>
        ) : null}
        <div>
          <Text strong>Console 退出关系</Text>
          <Paragraph style={{ marginBottom: 0 }}>
            {definition.consoleExitRelation}
          </Paragraph>
        </div>
      </Space>
    </Card>
  )
}
