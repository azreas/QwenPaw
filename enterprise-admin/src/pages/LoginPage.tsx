import React, { useState } from "react"
import { Form, Input, Button, Card, message, Spin } from "antd"
import { UserOutlined, LockOutlined } from "@ant-design/icons"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useAuth } from "@/features/auth/useAuth"
import { ApiError } from "@/api/http"

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()

  const redirectTo = searchParams.get("redirect") || "/dashboard"

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await login(values)
      message.success("登录成功")
      navigate(redirectTo, { replace: true })
    } catch (error) {
      const apiError = error as ApiError
      message.error(apiError.message || "登录失败，请检查用户名和密码")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        padding: 20,
      }}
    >
      <Card
        style={{
          width: "100%",
          maxWidth: 400,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.1)",
          borderRadius: 12,
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1
            style={{
              fontSize: 24,
              fontWeight: 600,
              marginBottom: 8,
              color: "#1f2937",
            }}
          >
            企业工作台
          </h1>
          <p style={{ color: "#6b7280", fontSize: 14, margin: 0 }}>
            欢迎使用 QwenPaw Enterprise Admin Console
          </p>
        </div>

        <Form
          form={form}
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[
              { required: true, message: "请输入用户名" },
              { min: 3, message: "用户名至少需要3个字符" },
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: "#9ca3af" }} />}
              placeholder="用户名"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: "请输入密码" },
              { min: 6, message: "密码至少需要6个字符" },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: "#9ca3af" }} />}
              placeholder="密码"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              loading={loading}
              style={{ height: 44, borderRadius: 8, fontWeight: 500 }}
            >
              {loading ? <Spin size="small" /> : "登录"}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default LoginPage
