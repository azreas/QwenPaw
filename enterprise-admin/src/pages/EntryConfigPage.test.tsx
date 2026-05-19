import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import EntryConfigPage from "./EntryConfigPage"
import {
  diagnoseTenantEntryConfig,
  getTenantEntryConfig,
  putTenantEntryConfig,
} from "@/api/entryConfig"
import { listWecomTenants } from "@/api/tenants"

vi.mock("@/api/entryConfig", () => ({
  diagnoseTenantEntryConfig: vi.fn(),
  getTenantEntryConfig: vi.fn(),
  putTenantEntryConfig: vi.fn(),
}))

vi.mock("@/api/tenants", () => ({
  listWecomTenants: vi.fn(),
}))

const tenant = {
  tenant_id: "acme",
  agent_id: "wx_acme",
  workspace_dir: "D:/tenants/wx_acme",
  exists: true,
  initialized: true,
  running: true,
  updated_at: "2026-05-13T08:00:00+00:00",
  chat_count: 3,
  job_count: 1,
  source: "workspace",
}

const entryConfig = {
  wecom: {
    enabled: true,
    bot_id: "bot-old",
    secret_set: true,
    media_dir: null,
    welcome_text: "hello",
    share_session_in_group: true,
    max_reconnect_attempts: -1,
    streaming_enabled: false,
    require_mention: false,
    dm_policy: "open",
    group_policy: "open",
    allow_from: ["corp-a"],
    deny_message: "",
  },
  webchat: {
    enabled: true,
    media_dir: "media",
    user_data_dir: "users",
    require_mention: false,
    dm_policy: "allowlist",
    group_policy: "open",
    allow_from: ["u1"],
    deny_message: "blocked",
    session_secret_source: "env",
    qrcode_config_source: "env",
  },
}

describe("EntryConfigPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [tenant] })
    vi.mocked(getTenantEntryConfig).mockResolvedValue(entryConfig)
    vi.mocked(putTenantEntryConfig).mockResolvedValue(entryConfig)
    vi.mocked(diagnoseTenantEntryConfig).mockResolvedValue({
      agent_id: "wx_acme",
      status: "ok",
      checks: { workspace_exists: true },
      messages: [],
    })
  })

  it("loads tenant entry config", async () => {
    render(<EntryConfigPage />)

    expect(await screen.findByRole("heading", { name: "入口配置" })).toBeInTheDocument()
    expect(screen.getByText("WebChat 平台级登录参数仍由环境变量管理")).toBeInTheDocument()
    await waitFor(() => {
      expect(getTenantEntryConfig).toHaveBeenCalledWith("wx_acme")
      expect(screen.getByLabelText("WeCom Bot ID")).toHaveValue("bot-old")
      expect(screen.getByLabelText("WebChat 允许来源")).toHaveValue("u1")
    })
  })

  it("saves tenant-local entry config and runs diagnostics", async () => {
    render(<EntryConfigPage />)

    await waitFor(() => {
      expect(screen.getByLabelText("WeCom Bot ID")).toHaveValue("bot-old")
    })
    const botId = screen.getByLabelText("WeCom Bot ID")
    await userEvent.clear(botId)
    await userEvent.type(botId, "bot-new")
    await userEvent.click(screen.getByRole("button", { name: "保存入口配置" }))

    await waitFor(() => {
      expect(putTenantEntryConfig).toHaveBeenCalledWith(
        "wx_acme",
        expect.objectContaining({
          wecom: expect.objectContaining({
            bot_id: "bot-new",
            allow_from: ["corp-a"],
          }),
          webchat: expect.objectContaining({
            allow_from: ["u1"],
          }),
        }),
      )
      expect(diagnoseTenantEntryConfig).toHaveBeenCalledWith("wx_acme")
    })
  })
})
