import { beforeEach, describe, expect, it, vi } from "vitest"
import { get, put } from "./http"
import {
  listPermissionDenials,
  listTenantPolicies,
  putTenantPolicy,
} from "./security"

vi.mock("./http", () => ({
  get: vi.fn(),
  put: vi.fn(),
}))

const policy = {
  policy_id: "default",
  display_name: "默认成员策略",
  allow_model_switch: true,
  allowed_models: [],
  allow_skill_create: true,
  allow_skill_upload_zip: true,
  allow_skill_hub_import: true,
  allow_tools: true,
  allowed_tools: [],
  allow_mcp: true,
  allowed_mcp_transports: ["sse", "http"],
  allow_tasks: true,
  max_cron_jobs: 20,
  min_cron_interval_minutes: 5,
  allow_task_run_now: true,
  allow_task_tools: true,
  task_timeout_seconds: 120,
  file_upload_limit_mb: 100,
  token_quota_monthly: null,
  advanced_config_enabled: false,
}

describe("security api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(get).mockResolvedValue({})
    vi.mocked(put).mockResolvedValue(policy)
  })

  it("loads policies and permission denials", async () => {
    await listTenantPolicies()
    await listPermissionDenials()

    expect(get).toHaveBeenNthCalledWith(1, "/platform/tenancy/policies")
    expect(get).toHaveBeenNthCalledWith(2, "/audit/events", {
      params: {
        event_type: "authz.denied",
        limit: 50,
      },
    })
  })

  it("updates policy with encoded policy id", async () => {
    await putTenantPolicy("default/a", policy)

    expect(put).toHaveBeenCalledWith(
      "/platform/tenancy/policies/default%2Fa",
      policy,
    )
  })
})
