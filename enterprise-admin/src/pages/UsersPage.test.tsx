import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import UsersPage from "./UsersPage"
import { createAdminUser, listAdminUsers, updateAdminUser } from "@/api/users"

vi.mock("@/api/users", () => ({
  createAdminUser: vi.fn(),
  listAdminUsers: vi.fn(),
  updateAdminUser: vi.fn(),
}))

const admin = {
  username: "admin",
  roles: ["platform_admin"],
  tenant_id: "",
  disabled: false,
}

const tenantUser = {
  username: "alice",
  roles: ["tenant_admin"],
  tenant_id: "acme",
  disabled: false,
}

describe("UsersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listAdminUsers).mockResolvedValue({ items: [admin, tenantUser] })
  })

  it("renders users and permission tabs", async () => {
    render(<UsersPage />)

    expect(
      await screen.findByRole("heading", { name: "用户与权限" }),
    ).toBeInTheDocument()
    expect(screen.getByText("admin")).toBeInTheDocument()
    expect(screen.getByText("租户管理员")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("tab", { name: "权限矩阵" }))
    expect(screen.getByText("auth_users:write")).toBeInTheDocument()
  })

  it("creates user", async () => {
    vi.mocked(createAdminUser).mockResolvedValue({
      username: "bob",
      roles: ["tenant_member"],
      tenant_id: "acme",
      disabled: false,
    })

    render(<UsersPage />)
    await userEvent.click(await screen.findByRole("button", { name: /新建用户/ }))
    await userEvent.type(screen.getByLabelText("用户名"), "bob")
    await userEvent.type(screen.getByLabelText("密码"), "secret")
    await userEvent.type(screen.getByLabelText("租户 ID"), "acme")
    await userEvent.click(screen.getByRole("button", { name: "确认" }))

    await waitFor(() => {
      expect(createAdminUser).toHaveBeenCalledWith({
        username: "bob",
        password: "secret",
        roles: ["tenant_member"],
        tenant_id: "acme",
      })
    })
  })

  it("updates disabled state", async () => {
    vi.mocked(updateAdminUser).mockResolvedValue({ ...tenantUser, disabled: true })

    render(<UsersPage />)
    await userEvent.click(await screen.findByRole("button", { name: "编辑 alice" }))
    await userEvent.click(screen.getByRole("switch", { name: "禁用用户" }))
    await userEvent.click(screen.getByRole("button", { name: "保存" }))

    await waitFor(() => {
      expect(updateAdminUser).toHaveBeenCalledWith("alice", {
        roles: ["tenant_admin"],
        tenant_id: "acme",
        disabled: true,
      })
    })
  })

  it("does not show internal page completeness details", async () => {
    render(<UsersPage />)

    expect(await screen.findByRole("heading", { name: "用户与权限" })).toBeInTheDocument()
    expect(screen.queryByText("页面完整性")).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
  })

  it("shows staged permission denial and token policy notes", async () => {
    render(<UsersPage />)

    expect(
      await screen.findByText(
        /权限拒绝审计、禁用用户后的 token 失效策略和自定义角色引用检查/,
      ),
    ).toBeInTheDocument()
  })
})
