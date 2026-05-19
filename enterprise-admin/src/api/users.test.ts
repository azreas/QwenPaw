import { beforeEach, describe, expect, it, vi } from "vitest"
import { get, patch, post } from "./http"
import { createAdminUser, listAdminUsers, updateAdminUser } from "./users"

vi.mock("./http", () => ({
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
}))

const user = {
  username: "alice",
  roles: ["tenant_admin"],
  tenant_id: "acme",
  disabled: false,
}

describe("users api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("lists admin users", async () => {
    vi.mocked(get).mockResolvedValue({ items: [user] })

    const result = await listAdminUsers()

    expect(get).toHaveBeenCalledWith("/auth/users")
    expect(result.items[0].username).toBe("alice")
  })

  it("creates admin user", async () => {
    vi.mocked(post).mockResolvedValue(user)

    await createAdminUser({
      username: "alice",
      password: "secret",
      roles: ["tenant_admin"],
      tenant_id: "acme",
    })

    expect(post).toHaveBeenCalledWith("/auth/users", {
      username: "alice",
      password: "secret",
      roles: ["tenant_admin"],
      tenant_id: "acme",
    })
  })

  it("updates admin user with encoded username", async () => {
    vi.mocked(patch).mockResolvedValue(user)

    await updateAdminUser("alice@example.com", { disabled: true })

    expect(patch).toHaveBeenCalledWith("/auth/users/alice%40example.com", {
      disabled: true,
    })
  })
})
