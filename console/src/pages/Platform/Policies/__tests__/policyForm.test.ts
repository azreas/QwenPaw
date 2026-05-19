import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { TenantPolicy } from "../../../../api/types/platformTenancy.ts";
import { formToPolicy, policyToForm } from "../policyForm.ts";

const basePolicy: TenantPolicy = {
  policy_id: "standard",
  display_name: "Standard",
  allow_model_switch: true,
  allowed_models: ["qwen-max", "qwen-plus"],
  allow_skill_create: true,
  allow_skill_upload_zip: false,
  allow_skill_hub_import: true,
  allow_tools: true,
  allowed_tools: ["search", "code"],
  allow_mcp: true,
  allowed_mcp_transports: ["stdio", "streamable_http"],
  allow_tasks: true,
  max_cron_jobs: 8,
  min_cron_interval_minutes: 15,
  allow_task_run_now: true,
  allow_task_tools: false,
  task_timeout_seconds: 600,
  file_upload_limit_mb: 128,
  token_quota_monthly: 1000000,
  advanced_config_enabled: false,
};

describe("policyForm", () => {
  it("round trips a complete tenant policy", () => {
    const form = policyToForm(basePolicy);
    const policy = formToPolicy(form, basePolicy);

    assert.deepEqual(policy, basePolicy);
  });

  it("keeps MCP and cron limits stable through form conversion", () => {
    const form = policyToForm({
      ...basePolicy,
      allow_mcp: false,
      allowed_mcp_transports: [],
      max_cron_jobs: 0,
    });

    assert.equal(form.allow_mcp, false);
    assert.deepEqual(form.allowed_mcp_transports, []);
    assert.equal(form.max_cron_jobs, 0);

    const policy = formToPolicy(form, basePolicy);
    assert.equal(policy.allow_mcp, false);
    assert.deepEqual(policy.allowed_mcp_transports, []);
    assert.equal(policy.max_cron_jobs, 0);
  });

  it("preserves an unset monthly token quota", () => {
    const form = policyToForm({
      ...basePolicy,
      token_quota_monthly: null,
    });

    const policy = formToPolicy(form, basePolicy);

    assert.equal(policy.token_quota_monthly, null);
  });
});
