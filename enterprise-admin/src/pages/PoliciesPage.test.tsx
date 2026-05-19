import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  deletePolicy,
  deleteTemplate,
  listPlatformTenants,
  listPolicies,
  listTemplates,
  savePolicy,
  saveTemplate,
} from "@/api/policies"
import PoliciesPage from "./PoliciesPage"

vi.mock("@/api/policies", () => ({
  deletePolicy: vi.fn(),
  deleteTemplate: vi.fn(),
  listPlatformTenants: vi.fn(),
  listPolicies: vi.fn(),
  listTemplates: vi.fn(),
  savePolicy: vi.fn(),
  saveTemplate: vi.fn(),
}))

const defaultPolicy = {
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

const safePolicy = {
  ...defaultPolicy,
  policy_id: "member-safe",
  display_name: "安全成员策略",
  allow_mcp: false,
}

const unusedPolicy = {
  ...defaultPolicy,
  policy_id: "unused-policy",
  display_name: "未引用策略",
}

const defaultTemplate = {
  template_id: "default",
  display_name: "默认成员模板",
  default_model: null,
  default_prompt_files: [],
  default_skills: [],
  default_tools: [],
  default_task_templates: [],
}

const starterTemplate = {
  ...defaultTemplate,
  template_id: "starter",
  display_name: "销售入门模板",
  default_model: "qwen-max",
  default_skills: ["sales_report"],
  default_tools: ["read_file"],
}

const unusedTemplate = {
  ...defaultTemplate,
  template_id: "unused-template",
  display_name: "未引用模板",
}

const tenants = [
  {
    tenant_id: "acme",
    display_name: "Acme",
    agent_id: "wx_acme",
    status: "active",
    source: "manual",
    policy_id: "member-safe",
    template_id: "starter",
    metadata: {},
    created_at: "2026-05-16T00:00:00+00:00",
    updated_at: "2026-05-16T00:00:00+00:00",
  },
]

describe("PoliciesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listPolicies).mockResolvedValue({
      policies: [defaultPolicy, safePolicy, unusedPolicy],
    })
    vi.mocked(listTemplates).mockResolvedValue({
      templates: [defaultTemplate, starterTemplate, unusedTemplate],
    })
    vi.mocked(listPlatformTenants).mockResolvedValue({ tenants })
    vi.mocked(savePolicy).mockResolvedValue(safePolicy)
    vi.mocked(saveTemplate).mockResolvedValue(starterTemplate)
    vi.mocked(deletePolicy).mockResolvedValue({ deleted: true })
    vi.mocked(deleteTemplate).mockResolvedValue({ deleted: true })
  })

  it("loads policies, templates, summaries and tenant impact preview", async () => {
    render(<PoliciesPage />)

    expect(
      await screen.findByRole("heading", { name: "策略配置" }),
    ).toBeInTheDocument()
    expect(screen.getByText("策略数")).toBeInTheDocument()
    expect(screen.getByText("模板数")).toBeInTheDocument()
    expect(screen.getByText("安全成员策略")).toBeInTheDocument()
    expect(screen.getByText("member-safe")).toBeInTheDocument()
    await userEvent.click(screen.getByText("安全成员策略"))
    expect(screen.getByText("Acme")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("tab", { name: "租户模板" }))
    expect(screen.getByText("销售入门模板")).toBeInTheDocument()
    expect(screen.getByText("starter")).toBeInTheDocument()
  })

  it("saves selected policy with normalized string lists", async () => {
    render(<PoliciesPage />)

    await userEvent.click(await screen.findByText("安全成员策略"))
    await userEvent.clear(screen.getByLabelText("策略名称"))
    await userEvent.type(screen.getByLabelText("策略名称"), "安全成员策略 v2")
    await userEvent.clear(screen.getByLabelText("允许模型"))
    await userEvent.type(screen.getByLabelText("允许模型"), "qwen-max, qwen-plus")
    await userEvent.click(screen.getByRole("button", { name: "保存策略" }))

    await waitFor(() => {
      expect(savePolicy).toHaveBeenCalledWith("member-safe", {
        ...safePolicy,
        display_name: "安全成员策略 v2",
        allowed_models: ["qwen-max", "qwen-plus"],
      })
    })
  })

  it("creates a new policy from the policy workspace", async () => {
    render(<PoliciesPage />)

    await userEvent.click(await screen.findByRole("button", { name: "新建策略" }))
    expect(screen.getByLabelText("策略名称")).toHaveValue("新建成员策略")
    expect(screen.getByText("新建项保存后可被租户引用")).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText("策略 ID"))
    await userEvent.type(screen.getByLabelText("策略 ID"), "custom-policy")
    await userEvent.clear(screen.getByLabelText("策略名称"))
    await userEvent.type(screen.getByLabelText("策略名称"), "自定义策略")
    await userEvent.clear(screen.getByLabelText("允许工具"))
    await userEvent.type(screen.getByLabelText("允许工具"), "read_file, search")
    await userEvent.click(screen.getByRole("button", { name: "保存策略" }))

    await waitFor(() => {
      expect(savePolicy).toHaveBeenCalledWith(
        "custom-policy",
        expect.objectContaining({
          policy_id: "custom-policy",
          display_name: "自定义策略",
          allowed_tools: ["read_file", "search"],
        }),
      )
    })
  })

  it("keeps existing policy id read-only while allowing new policy id input", async () => {
    render(<PoliciesPage />)

    await userEvent.click(await screen.findByText("安全成员策略"))
    expect(screen.getByLabelText("策略 ID")).toBeDisabled()

    await userEvent.click(screen.getByRole("button", { name: "新建策略" }))
    expect(screen.getByLabelText("策略 ID")).toBeEnabled()
  })

  it("saves selected template with parsed task templates", async () => {
    render(<PoliciesPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "租户模板" }))
    await userEvent.click(screen.getByText("销售入门模板"))
    await userEvent.clear(screen.getByLabelText("默认模型"))
    await userEvent.type(screen.getByLabelText("默认模型"), "qwen-plus")
    fireEvent.change(screen.getByLabelText("默认任务模板 JSON"), {
      target: { value: JSON.stringify([{ name: "日报" }]) },
    })
    await userEvent.click(screen.getByRole("button", { name: "保存模板" }))

    await waitFor(() => {
      expect(saveTemplate).toHaveBeenCalledWith("starter", {
        ...starterTemplate,
        default_model: "qwen-plus",
        default_task_templates: [{ name: "日报" }],
      })
    })
  })

  it("creates a new template from the template workspace", async () => {
    render(<PoliciesPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "租户模板" }))
    await userEvent.click(screen.getByRole("button", { name: "新建模板" }))
    expect(screen.getByLabelText("模板名称")).toHaveValue("新建成员模板")
    expect(screen.getByText("新建项保存后可被租户引用")).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText("模板 ID"))
    await userEvent.type(screen.getByLabelText("模板 ID"), "sales-starter")
    await userEvent.clear(screen.getByLabelText("模板名称"))
    await userEvent.type(screen.getByLabelText("模板名称"), "销售模板")
    await userEvent.clear(screen.getByLabelText("默认 Skills"))
    await userEvent.type(screen.getByLabelText("默认 Skills"), "sales_report")
    await userEvent.click(screen.getByRole("button", { name: "保存模板" }))

    await waitFor(() => {
      expect(saveTemplate).toHaveBeenCalledWith(
        "sales-starter",
        expect.objectContaining({
          template_id: "sales-starter",
          display_name: "销售模板",
          default_skills: ["sales_report"],
        }),
      )
    })
  })

  it("blocks invalid template task JSON", async () => {
    render(<PoliciesPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "租户模板" }))
    await userEvent.click(screen.getByText("销售入门模板"))
    fireEvent.change(screen.getByLabelText("默认任务模板 JSON"), {
      target: { value: "{bad" },
    })
    await userEvent.click(screen.getByRole("button", { name: "保存模板" }))

    expect(
      (await screen.findAllByText("任务模板必须是 JSON 数组")).length,
    ).toBeGreaterThan(0)
    expect(saveTemplate).not.toHaveBeenCalled()
  })

  it("guards default and referenced deletes while allowing unused deletes", async () => {
    render(<PoliciesPage />)

    expect(await screen.findByText("默认成员策略")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "删除策略" })).toBeDisabled()
    expect(screen.getAllByText("默认项不可删除").length).toBeGreaterThan(0)

    await userEvent.click(screen.getByText("安全成员策略"))
    expect(screen.getByRole("button", { name: "删除策略" })).toBeDisabled()
    expect(screen.getByText("仍被 1 个租户引用")).toBeInTheDocument()

    await userEvent.click(screen.getByText("未引用策略"))
    expect(screen.getByRole("button", { name: "删除策略" })).toBeEnabled()
    await userEvent.click(screen.getByRole("button", { name: "删除策略" }))
    await waitFor(() => {
      expect(deletePolicy).toHaveBeenCalledWith("unused-policy")
    })

    await userEvent.click(screen.getByRole("tab", { name: "租户模板" }))
    expect(screen.getByRole("button", { name: "删除模板" })).toBeDisabled()
    expect(screen.getAllByText("默认项不可删除").length).toBeGreaterThan(0)

    await userEvent.click(screen.getByText("销售入门模板"))
    expect(screen.getByRole("button", { name: "删除模板" })).toBeDisabled()

    await userEvent.click(screen.getByText("未引用模板"))
    expect(screen.getByRole("button", { name: "删除模板" })).toBeEnabled()
    await userEvent.click(screen.getByRole("button", { name: "删除模板" }))
    await waitFor(() => {
      expect(deleteTemplate).toHaveBeenCalledWith("unused-template")
    })
  })

  it("does not show all tenants as impact when selected item has no references", async () => {
    render(<PoliciesPage />)

    await userEvent.click(await screen.findByText("未引用策略"))

    expect(screen.queryByText("Acme")).not.toBeInTheDocument()
    expect(screen.getByText("暂无受影响租户")).toBeInTheDocument()
  })
})
