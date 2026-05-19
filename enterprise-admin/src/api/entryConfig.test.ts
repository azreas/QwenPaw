import { beforeEach, describe, expect, it, vi } from "vitest"
import { get, post, put } from "./http"
import {
  diagnoseTenantEntryConfig,
  getTenantEntryConfig,
  putTenantEntryConfig,
} from "./entryConfig"

vi.mock("./http", () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}))

const payload = {
  wecom: {
    enabled: true,
    bot_id: "bot",
    secret: "",
    secret_set: true,
    media_dir: null,
    welcome_text: "hi",
    share_session_in_group: false,
    max_reconnect_attempts: -1,
    streaming_enabled: true,
    require_mention: true,
    dm_policy: "open",
    group_policy: "open",
    allow_from: ["corp"],
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
  },
}

describe("entry config api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads, saves and diagnoses tenant entry config with encoded agent id", async () => {
    vi.mocked(get).mockResolvedValue(payload)
    vi.mocked(put).mockResolvedValue(payload)
    vi.mocked(post).mockResolvedValue({ agent_id: "wx demo/a", status: "ok" })

    await getTenantEntryConfig("wx demo/a")
    await putTenantEntryConfig("wx demo/a", payload)
    await diagnoseTenantEntryConfig("wx demo/a")

    expect(get).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/entry-config",
    )
    expect(put).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/entry-config",
      payload,
    )
    expect(post).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/entry-config/diagnose",
    )
  })
})
