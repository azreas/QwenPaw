import { beforeEach, describe, expect, it, vi } from "vitest"
import { del, get, put } from "./http"
import {
  deleteTenantTemplate,
  getTenantSecuritySettings,
  getTenantSystemPrompts,
  listTenantTemplates,
  putTenantSecuritySettings,
  putTenantSystemPrompts,
  upsertTenantTemplate,
} from "./agentConfig"

vi.mock("./http", () => ({
  del: vi.fn(),
  get: vi.fn(),
  put: vi.fn(),
}))

const template = {
  template_id: "starter",
  display_name: "Starter",
  default_model: "qwen-max",
  default_prompt_files: ["AGENTS.md"],
  default_skills: ["sales_report"],
  default_tools: ["read_file"],
  default_task_templates: [],
}

describe("agent config api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("manages platform templates", async () => {
    vi.mocked(get).mockResolvedValue({ templates: [template] })
    vi.mocked(put).mockResolvedValue(template)
    vi.mocked(del).mockResolvedValue({ deleted: true })

    await listTenantTemplates()
    await upsertTenantTemplate("starter/a", template)
    await deleteTenantTemplate("starter/a")

    expect(get).toHaveBeenCalledWith("/platform/tenancy/templates")
    expect(put).toHaveBeenCalledWith(
      "/platform/tenancy/templates/starter%2Fa",
      template,
    )
    expect(del).toHaveBeenCalledWith("/platform/tenancy/templates/starter%2Fa")
  })

  it("loads and saves tenant-local agent configuration", async () => {
    vi.mocked(get).mockResolvedValueOnce({ files: ["AGENTS.md"] }).mockResolvedValueOnce({
      approval_level: "SMART",
      tool_guard_rules: [],
    })
    vi.mocked(put).mockResolvedValue({})

    await getTenantSystemPrompts("wx demo/a")
    await getTenantSecuritySettings("wx demo/a")
    await putTenantSystemPrompts("wx demo/a", { files: ["AGENTS.md", "SOUL.md"] })
    await putTenantSecuritySettings("wx demo/a", {
      approval_level: "AUTO",
      tool_guard_rules: [],
    })

    expect(get).toHaveBeenNthCalledWith(
      1,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/system-prompts",
    )
    expect(get).toHaveBeenNthCalledWith(
      2,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/security",
    )
    expect(put).toHaveBeenNthCalledWith(
      1,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/system-prompts",
      { files: ["AGENTS.md", "SOUL.md"] },
    )
    expect(put).toHaveBeenNthCalledWith(
      2,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/security",
      { approval_level: "AUTO", tool_guard_rules: [] },
    )
  })
})
