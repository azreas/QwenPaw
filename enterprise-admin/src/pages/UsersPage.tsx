import React, { useCallback, useEffect, useMemo, useState } from "react"
import {
  Card,
  Table,
  Button,
  Modal,
  Drawer,
  Tag,
  Statistic,
  Row,
  Col,
  Switch,
  Input,
  Form,
  Select,
  Tabs,
  Checkbox,
  message,
  Spin,
  Alert,
  Descriptions,
  Typography,
} from "antd"
import { UserAddOutlined } from "@ant-design/icons"
import { listAdminUsers, createAdminUser, updateAdminUser } from "@/api/users"
import { ApiError } from "@/api/http"
import {
  DEFAULT_ROLE_DEFINITIONS,
  buildUserStats,
  buildPermissionMatrix,
  getRoleLabel,
  normalizeUserRoles,
} from "@/features/users/rbacModel"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"
import type {
  DefaultRole,
  PermissionMatrixRow,
  UserStats,
} from "@/features/users/rbacModel"
import type { AdminUser } from "@/api/types"

const { Title } = Typography

/** 统一处理用户管理操作的 403 提示 */
function getUserManagementErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.isForbidden()) {
    return "当前身份无权管理用户或认证未启用"
  }
  return err instanceof Error ? err.message : "操作失败"
}

/** 角色候选项，来自 DEFAULT_ROLE_DEFINITIONS 的 key，不在页面硬编码第二份角色列表 */
const ROLE_OPTIONS: DefaultRole[] = Object.keys(
  DEFAULT_ROLE_DEFINITIONS,
) as DefaultRole[]

/** 角色下拉选项 */
const ROLE_SELECT_OPTIONS = ROLE_OPTIONS.map((r) => ({
  label: getRoleLabel(r),
  value: r,
}))

const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /* ── 新建用户 Modal ── */
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createForm] = Form.useForm()
  const [creating, setCreating] = useState(false)

  /* ── 编辑用户 Drawer ── */
  const [editDrawerOpen, setEditDrawerOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)
  const [editForm] = Form.useForm()
  const [saving, setSaving] = useState(false)

  /* ── 权限矩阵（静态计算） ── */
  const permissionMatrix = useMemo<PermissionMatrixRow[]>(
    () => buildPermissionMatrix(),
    [],
  )

  /* ── 加载用户列表 ── */
  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listAdminUsers()
      setUsers(data.items)
    } catch (err) {
      if (err instanceof ApiError && err.isForbidden()) {
        setError("当前身份无权管理用户或认证未启用")
      } else {
        setError(err instanceof Error ? err.message : "加载用户列表失败")
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const stats: UserStats = useMemo(() => buildUserStats(users), [users])

  /* ── 新建用户 ── */
  const openCreateModal = () => {
    createForm.resetFields()
    setCreateModalOpen(true)
  }

  const closeCreateModal = () => {
    setCreateModalOpen(false)
  }

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields()
      setCreating(true)
      await createAdminUser({
        username: values.username,
        password: values.password,
        roles: normalizeUserRoles(values.roles || []),
        tenant_id: values.tenant_id ?? "",
      })
      message.success("用户创建成功")
      closeCreateModal()
      createForm.resetFields()
      fetchUsers()
    } catch (err) {
      if (err instanceof ApiError) {
        message.error(getUserManagementErrorMessage(err))
      }
      // 表单验证失败由 Ant Design 自动展示，无需额外处理
    } finally {
      setCreating(false)
    }
  }

  /* ── 编辑用户 ── */
  const openEditDrawer = (user: AdminUser) => {
    setEditingUser(user)
    editForm.setFieldsValue({
      roles: user.roles,
      tenant_id: user.tenant_id,
      disabled: user.disabled,
    })
    setEditDrawerOpen(true)
  }

  const closeEditDrawer = () => {
    setEditDrawerOpen(false)
    setEditingUser(null)
  }

  const handleSave = async () => {
    if (!editingUser) return
    try {
      const values = await editForm.validateFields()
      setSaving(true)
      await updateAdminUser(editingUser.username, {
        roles: normalizeUserRoles(values.roles || []),
        tenant_id: values.tenant_id,
        disabled: values.disabled,
      })
      message.success("用户更新成功")
      closeEditDrawer()
      fetchUsers()
    } catch (err) {
      if (err instanceof ApiError) {
        message.error(getUserManagementErrorMessage(err))
      }
    } finally {
      setSaving(false)
    }
  }

  /* ── 用户表格列 ── */
  const userColumns = [
    { title: "用户名", dataIndex: "username", key: "username" },
    {
      title: "角色",
      dataIndex: "roles",
      key: "roles",
      render: (roles: string[]) =>
        roles.map((role) => (
          <Tag key={role} color="blue">
            {getRoleLabel(role)}
          </Tag>
        )),
    },
    {
      title: "租户 ID",
      dataIndex: "tenant_id",
      key: "tenant_id",
      render: (text: string) => text || "-",
    },
    {
      title: "状态",
      dataIndex: "disabled",
      key: "disabled",
      render: (disabled: boolean) => (
        <Tag color={disabled ? "red" : "green"}>
          {disabled ? "禁用" : "启用"}
        </Tag>
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record: AdminUser) => (
        <Button
          type="link"
          size="small"
          aria-label={`编辑 ${record.username}`}
          onClick={() => openEditDrawer(record)}
        >
          编辑
        </Button>
      ),
    },
  ]

  /* ── 权限矩阵表格列 ── */
  const matrixColumns = [
    { title: "权限", dataIndex: "permission", key: "permission" },
    {
      title: "平台管理员",
      dataIndex: "platform_admin",
      key: "platform_admin",
      render: (checked: boolean) => <Checkbox checked={checked} disabled />,
    },
    {
      title: "租户管理员",
      dataIndex: "tenant_admin",
      key: "tenant_admin",
      render: (checked: boolean) => <Checkbox checked={checked} disabled />,
    },
    {
      title: "租户成员",
      dataIndex: "tenant_member",
      key: "tenant_member",
      render: (checked: boolean) => <Checkbox checked={checked} disabled />,
    },
    {
      title: "租户只读",
      dataIndex: "tenant_readonly",
      key: "tenant_readonly",
      render: (checked: boolean) => <Checkbox checked={checked} disabled />,
    },
  ]

  /* ── 加载中 ── */
  if (loading && users.length === 0) {
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

  /* ── 403 或其他加载错误 ── */
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

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        用户与权限
      </Title>

      <div style={{ marginBottom: 24 }}>
        <PageCompletenessPanel pageKey="users" compact />
      </div>

      <Alert
        type="info"
        showIcon
        message="权限治理阶段化开放"
        description="权限拒绝审计、禁用用户后的 token 失效策略和自定义角色引用检查将以只读说明和审计查询优先接入；当前页面已支持用户、角色和租户绑定管理。"
        style={{ marginBottom: 24 }}
      />

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="用户总数" value={stats.total} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="启用用户"
              value={stats.enabled}
              valueStyle={{ color: "#52c41a" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="禁用用户"
              value={stats.disabled}
              valueStyle={{ color: "#ff4d4f" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="平台管理员" value={stats.platformAdmins} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="已绑定租户" value={stats.tenantScoped} />
          </Card>
        </Col>
      </Row>

      {/* 选项卡：用户列表 / 角色目录 / 权限矩阵 */}
      <Tabs
        defaultActiveKey="users"
        items={[
          {
            key: "users",
            label: "用户列表",
            children: (
              <Card
                extra={
                  <Button
                    type="primary"
                    icon={<UserAddOutlined />}
                    onClick={openCreateModal}
                  >
                    新建用户
                  </Button>
                }
              >
                <Table
                  dataSource={users}
                  columns={userColumns}
                  rowKey="username"
                  loading={loading}
                  pagination={false}
                />
              </Card>
            ),
          },
          {
            key: "roles",
            label: "角色目录",
            children: (
              <Row gutter={[16, 16]}>
                {ROLE_OPTIONS.map((role) => {
                  const permissions = DEFAULT_ROLE_DEFINITIONS[role] as readonly string[]
                  return (
                    <Col xs={24} sm={12} lg={6} key={role}>
                      <Card title={getRoleLabel(role)} size="small">
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="角色标识">
                            {role}
                          </Descriptions.Item>
                          <Descriptions.Item label="权限数量">
                            {permissions.length}
                          </Descriptions.Item>
                        </Descriptions>
                      </Card>
                    </Col>
                  )
                })}
              </Row>
            ),
          },
          {
            key: "matrix",
            label: "权限矩阵",
            children: (
              <Card>
                <Table
                  dataSource={permissionMatrix}
                  columns={matrixColumns}
                  rowKey="permission"
                  pagination={false}
                  size="small"
                />
              </Card>
            ),
          },
        ]}
      />

      {/* 新建用户 Modal — footer={null} + 内嵌按钮确保测试可访问 */}
      <Modal
        title="新建用户"
        open={createModalOpen}
        onCancel={closeCreateModal}
        getContainer={false}
        footer={null}
      >
        <Form
          form={createForm}
          layout="vertical"
          initialValues={{ roles: ["tenant_member"] }}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input type="password" />
          </Form.Item>
          <Form.Item name="roles" label="角色">
            <Select mode="multiple" options={ROLE_SELECT_OPTIONS} />
          </Form.Item>
          <Form.Item name="tenant_id" label="租户 ID">
            <Input />
          </Form.Item>
        </Form>
        <div style={{ textAlign: "right" }}>
          <Button onClick={closeCreateModal} style={{ marginRight: 8 }}>
            取消
          </Button>
          <Button
            type="primary"
            onClick={handleCreate}
            loading={creating}
            aria-label="确认"
          >
            确认
          </Button>
        </div>
      </Modal>

      {/* 编辑用户 Drawer — footer={null} + 内嵌按钮确保测试可访问 */}
      <Drawer
        title={editingUser ? `编辑 ${editingUser.username}` : "编辑用户"}
        open={editDrawerOpen}
        onClose={closeEditDrawer}
        width={400}
        getContainer={false}
        footer={null}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="roles" label="角色">
            <Select mode="multiple" options={ROLE_SELECT_OPTIONS} />
          </Form.Item>
          <Form.Item name="tenant_id" label="租户 ID">
            <Input />
          </Form.Item>
          <Form.Item name="disabled" label="禁用用户" valuePropName="checked">
            <Switch aria-label="禁用用户" />
          </Form.Item>
        </Form>
        <div style={{ textAlign: "right" }}>
          <Button onClick={closeEditDrawer} style={{ marginRight: 8 }}>
            取消
          </Button>
          <Button
            type="primary"
            onClick={handleSave}
            loading={saving}
            aria-label="保存"
          >
            保存
          </Button>
        </div>
      </Drawer>
    </div>
  )
}

export default UsersPage
