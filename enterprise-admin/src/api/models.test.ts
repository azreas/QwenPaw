import { beforeEach, describe, expect, it, vi } from "vitest"
import { get, put } from "./http"
import {
  getTenantLlmRouting,
  getTenantModel,
  putTenantLlmRouting,
  putTenantModel,
} from "./models"

vi.mock("./http", () => ({
  get: vi.fn(),
  put: vi.fn(),
}))

describe("models api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads tenant model and routing with encoded agent id", async () => {
    vi.mocked(get).mockResolvedValue({})

    await getTenantModel("wx demo/a")
    await getTenantLlmRouting("wx demo/a")

    expect(get).toHaveBeenNthCalledWith(
      1,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/model",
    )
    expect(get).toHaveBeenNthCalledWith(
      2,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/llm-routing",
    )
  })

  it("updates tenant model and routing", async () => {
    vi.mocked(put).mockResolvedValue({})

    await putTenantModel("wx_demo", { provider_id: "dashscope", model: "qwen-max" })
    await putTenantLlmRouting("wx_demo", {
      enabled: true,
      mode: "cloud_first",
      local: { provider_id: "ollama", model: "qwen2.5" },
      cloud: { provider_id: "dashscope", model: "qwen-max" },
    })

    expect(put).toHaveBeenNthCalledWith(
      1,
      "/config/channels/wecom_tenant/tenants/wx_demo/model",
      { provider_id: "dashscope", model: "qwen-max" },
    )
    expect(put).toHaveBeenNthCalledWith(
      2,
      "/config/channels/wecom_tenant/tenants/wx_demo/llm-routing",
      {
        enabled: true,
        mode: "cloud_first",
        local: { provider_id: "ollama", model: "qwen2.5" },
        cloud: { provider_id: "dashscope", model: "qwen-max" },
      },
    )
  })
})
