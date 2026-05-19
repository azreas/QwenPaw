import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import ModelsPage from "./ModelsPage"
import {
  getTenantLlmRouting,
  getTenantModel,
  putTenantLlmRouting,
  putTenantModel,
} from "@/api/models"
import { listWecomTenants } from "@/api/tenants"

vi.mock("@/api/tenants", () => ({
  listWecomTenants: vi.fn(),
}))

vi.mock("@/api/models", () => ({
  getTenantLlmRouting: vi.fn(),
  getTenantModel: vi.fn(),
  putTenantLlmRouting: vi.fn(),
  putTenantModel: vi.fn(),
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

describe("ModelsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [tenant] })
    vi.mocked(getTenantModel).mockResolvedValue({
      provider_id: "dashscope",
      model: "qwen-max",
    })
    vi.mocked(getTenantLlmRouting).mockResolvedValue({
      enabled: true,
      mode: "cloud_first",
      local: { provider_id: "ollama", model: "qwen2.5" },
      cloud: { provider_id: "dashscope", model: "qwen-max" },
    })
    vi.mocked(putTenantModel).mockResolvedValue({
      provider_id: "dashscope",
      model: "qwen-plus",
    })
    vi.mocked(putTenantLlmRouting).mockResolvedValue({
      enabled: true,
      mode: "cloud_first",
      local: { provider_id: "ollama", model: "qwen2.5" },
      cloud: { provider_id: "dashscope", model: "qwen-plus" },
    })
  })

  it("loads tenant model and routing", async () => {
    render(<ModelsPage />)

    expect(await screen.findByRole("heading", { name: "模型治理" })).toBeInTheDocument()
    expect(screen.getByText("平台模型库存阶段化开放")).toBeInTheDocument()
    await waitFor(() => {
      expect(getTenantModel).toHaveBeenCalledWith("wx_acme")
      expect(getTenantLlmRouting).toHaveBeenCalledWith("wx_acme")
    })
    await waitFor(() => {
      expect(screen.getByLabelText("Model")).toHaveValue("qwen-max")
      expect(screen.getByLabelText("Cloud Model")).toHaveValue("qwen-max")
    })
  })

  it("saves active model", async () => {
    render(<ModelsPage />)

    await waitFor(() => {
      expect(screen.getByLabelText("Model")).toHaveValue("qwen-max")
    })
    const modelInput = screen.getByLabelText("Model")
    await userEvent.click(modelInput)
    await userEvent.clear(modelInput)
    await userEvent.type(modelInput, "qwen-plus")
    await userEvent.click(screen.getByRole("button", { name: "保存 Active Model" }))

    await waitFor(() => {
      expect(putTenantModel).toHaveBeenCalledWith("wx_acme", {
        provider_id: "dashscope",
        model: "qwen-plus",
      })
    })
  })

  it("saves routing", async () => {
    render(<ModelsPage />)

    await waitFor(() => {
      expect(screen.getByLabelText("Cloud Model")).toHaveValue("qwen-max")
    })
    const cloudModelInput = screen.getByLabelText("Cloud Model")
    await userEvent.clear(cloudModelInput)
    await userEvent.type(cloudModelInput, "qwen-plus")
    await userEvent.click(screen.getByRole("button", { name: "保存模型路由" }))

    await waitFor(() => {
      expect(putTenantLlmRouting).toHaveBeenCalledWith("wx_acme", {
        enabled: true,
        mode: "cloud_first",
        local: { provider_id: "ollama", model: "qwen2.5" },
        cloud: { provider_id: "dashscope", model: "qwen-plus" },
      })
    })
  })
})
