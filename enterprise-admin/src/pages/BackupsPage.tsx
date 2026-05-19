import React, { useEffect, useState } from "react"
import { Alert, Button, Card, Descriptions, Space, Table, Tag, Typography, message } from "antd"
import {
  getBackupDetail,
  getBackupProductionPolicy,
  listBackups,
  runBackupRestoreDrill,
} from "@/api/backups"
import type { BackupDetail, BackupMeta, BackupProductionPolicy } from "@/api/types"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

const BackupsPage: React.FC = () => {
  const [backups, setBackups] = useState<BackupMeta[]>([])
  const [policy, setPolicy] = useState<BackupProductionPolicy | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<BackupDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [drillLoadingId, setDrillLoadingId] = useState("")

  const loadBackups = async () => {
    try {
      setLoading(true)
      const [backupResp, policyResp] = await Promise.all([
        listBackups(),
        getBackupProductionPolicy(),
      ])
      setBackups(backupResp)
      setPolicy(policyResp)
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载备份恢复失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadBackups()
  }, [])

  const viewDetail = async (backupId: string) => {
    try {
      setSelectedDetail(await getBackupDetail(backupId))
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载备份详情失败")
    }
  }

  const runDrill = async (backupId: string) => {
    try {
      setDrillLoadingId(backupId)
      const result = await runBackupRestoreDrill(backupId)
      message.success(`恢复演练已完成：${result.sandbox_dir || backupId}`)
    } catch (err) {
      message.error(err instanceof Error ? err.message : "恢复演练失败")
    } finally {
      setDrillLoadingId("")
    }
  }

  return (
    <div className="enterprise-page">
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            备份恢复
          </Title>
          <Text type="secondary">备份列表、生产策略和恢复演练</Text>
        </div>

        <PageCompletenessPanel pageKey="backups" compact />

        <Alert
          type="warning"
          showIcon
          message="真实恢复与删除暂不开放"
          description="当前页面只开放只读备份列表、详情、生产策略和恢复演练。真实 restore、delete、import 需要补齐确认流程和审计事件后再开放。"
        />

        <Card title="生产备份策略" loading={loading}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="计划">
              {policy?.schedule || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="保留天数">
              {policy?.retention_days ?? "-"}
            </Descriptions.Item>
            <Descriptions.Item label="远端存储">
              {policy?.remote_store || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="完整性">
              {policy?.integrity || "-"}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title="备份列表" loading={loading}>
          <Table
            rowKey="id"
            dataSource={backups}
            pagination={{ pageSize: 8 }}
            columns={[
              {
                title: "备份",
                dataIndex: "name",
                render: (value: string, record) => (
                  <Space direction="vertical" size={0}>
                    <Text strong>{value}</Text>
                    <Text type="secondary">{record.id}</Text>
                  </Space>
                ),
              },
              { title: "Agent 数", dataIndex: "agent_count" },
              { title: "版本", dataIndex: "qwenpaw_version" },
              { title: "创建时间", dataIndex: "created_at" },
              {
                title: "范围",
                render: (_, record) => (
                  <Space wrap>
                    {record.scope.include_agents && <Tag>Agents</Tag>}
                    {record.scope.include_global_config && <Tag>Config</Tag>}
                    {record.scope.include_skill_pool && <Tag>Skills</Tag>}
                    {record.scope.include_secrets && <Tag color="red">Secrets</Tag>}
                  </Space>
                ),
              },
              {
                title: "操作",
                render: (_, record) => (
                  <Space>
                    <Button size="small" onClick={() => viewDetail(record.id)}>
                      详情
                    </Button>
                    <Button
                      size="small"
                      loading={drillLoadingId === record.id}
                      onClick={() => runDrill(record.id)}
                    >
                      恢复演练
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>

        {selectedDetail && (
          <Card title="备份详情">
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="ID">{selectedDetail.id}</Descriptions.Item>
              <Descriptions.Item label="说明">
                {selectedDetail.description || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Workspace Stats">
                <pre style={{ margin: 0 }}>
                  {JSON.stringify(selectedDetail.workspace_stats, null, 2)}
                </pre>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Space>
    </div>
  )
}

export default BackupsPage
