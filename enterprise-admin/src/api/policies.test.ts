import { beforeEach, describe, expect, it, vi } from "vitest"
import { del, get, put } from "./http"
import {
  deletePolicy,
  deleteTemplate,
  listPlatformTenants,
  listPolicies,
  listTemplates,
  savePolicy,
  saveTemplate,
} from "./policies"

vi.mock("./http", () => ({
  del: vi.fn(),
  get: vi.fn(),
  put: vi.fn(),
}))

const policy = {
  policy_id: "default",
  display_name: "默认策略",
  allow_model_switch: true,
  allowed_models: ["qwen-max"],
  allow_skill_create: true,
  allow_skill_upload_zip: true,
  allow_skill_hub_import: true,
  allow_tools: true,
  allowed_tools: ["read_file"],
  allow_mcp: true,
  allowed_mcp_transports: ["sse"],
  allow_tasks: true,
  max_cron_jobs: 10,
  min_cron_interval_minutes: 5,
  allow_task_run_now: true,
  allow_task_tools: true,
  task_timeout_seconds: 120,
  file_upload_limit_mb: 100,
  token_quota_monthly: null,
  advanced_config_enabled: false,
}

const template = {
  template_id: "starter",
  display_name: "Starter",
  default_model: "qwen-max",
  default_prompt_files: ["AGENTS.md"],
  default_skills: ["sales_report"],
  default_tools: ["read_file"],
  default_task_templates: [],
}

const tenant = {
  tenant_id: "tenant-a",
  tenant_name: "Tenant A",
  policy_id: "default",
  template_id: "starter",
  agent_id: "wx_tenant_a",
  status: "running",
}

describe("policies api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("lists policies templates and platform tenants", async () => {
    vi.mocked(get)
      .mockResolvedValueOnce({ policies: [policy] })
      .mockResolvedValueOnce({ templates: [template] })
      .mockResolvedValueOnce({ tenants: [tenant] })

    await listPolicies()
    await listTemplates()
    await listPlatformTenants()

    expect(get).toHaveBeenNthCalledWith(1, "/platform/tenancy/policies")
    expect(get).toHaveBeenNthCalledWith(2, "/platform/tenancy/templates")
    expect(get).toHaveBeenNthCalledWith(3, "/platform/tenancy/tenants")
  })

  it("saves and deletes policy with encoded policy id", async () => {
    vi.mocked(put).mockResolvedValue(policy)
    vi.mocked(del).mockResolvedValue({ deleted: true })

    await savePolicy("default/a b", policy)
    await deletePolicy("default/a b")

    expect(put).toHaveBeenCalledWith(
      "/platform/tenancy/policies/default%2Fa%20b",
      policy,
    )
    expect(del).toHaveBeenCalledWith(
      "/platform/tenancy/policies/default%2Fa%20b",
    )
  })

  it("saves and deletes template with encoded template id", async () => {
    vi.mocked(put).mockResolvedValue(template)
    vi.mocked(del).mockResolvedValue({ deleted: true })

    await saveTemplate("starter/a b", template)
    await deleteTemplate("starter/a b")

    expect(put).toHaveBeenCalledWith(
      "/platform/tenancy/templates/starter%2Fa%20b",
      template,
    )
    expect(del).toHaveBeenCalledWith(
      "/platform/tenancy/templates/starter%2Fa%20b",
    )
  })
})
