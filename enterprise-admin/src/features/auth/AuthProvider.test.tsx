import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { AuthProvider, useAuth } from "./AuthProvider"

const mockGetAuthStatus = vi.fn()

vi.mock("@/api/auth", () => ({
  getAuthStatus: () => mockGetAuthStatus(),
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock("@/api/authToken", () => ({
  clearAuthToken: vi.fn(),
}))

function TestConsumer() {
  const { isAuthenticated, loading, user } = useAuth()
  return (
    <div>
      <span data-testid="loading">{loading ? "loading" : "done"}</span>
      <span data-testid="auth">{isAuthenticated ? "authenticated" : "unauthenticated"}</span>
      <span data-testid="authDisabled">{user?.authDisabled ? "disabled" : "enabled"}</span>
    </div>
  )
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("后端认证未启用时应视为已认证", async () => {
    mockGetAuthStatus.mockResolvedValue({
      authenticated: false,
      authDisabled: true,
    })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() =>
      expect(screen.getByTestId("loading").textContent).toBe("done"),
    )

    expect(screen.getByTestId("auth").textContent).toBe("authenticated")
    expect(screen.getByTestId("authDisabled").textContent).toBe("disabled")
  })

  it("正常认证通过时应为已认证", async () => {
    mockGetAuthStatus.mockResolvedValue({
      authenticated: true,
      username: "admin",
      role: "platform_admin",
    })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() =>
      expect(screen.getByTestId("loading").textContent).toBe("done"),
    )

    expect(screen.getByTestId("auth").textContent).toBe("authenticated")
    expect(screen.getByTestId("authDisabled").textContent).toBe("enabled")
  })

  it("未认证且认证已启用时应为未认证", async () => {
    mockGetAuthStatus.mockResolvedValue({
      authenticated: false,
    })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() =>
      expect(screen.getByTestId("loading").textContent).toBe("done"),
    )

    expect(screen.getByTestId("auth").textContent).toBe("unauthenticated")
  })

  it("getAuthStatus 异常时应为未认证", async () => {
    mockGetAuthStatus.mockRejectedValue(new Error("Network error"))

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() =>
      expect(screen.getByTestId("loading").textContent).toBe("done"),
    )

    expect(screen.getByTestId("auth").textContent).toBe("unauthenticated")
  })
})
