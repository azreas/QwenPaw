import type { TenantPolicy } from "../../../api/types/platformTenancy";

export type PolicyFormValues = TenantPolicy;

const emptyPolicy: TenantPolicy = {
  policy_id: "",
  display_name: "",
  allow_model_switch: false,
  allowed_models: [],
  allow_skill_create: false,
  allow_skill_upload_zip: false,
  allow_skill_hub_import: false,
  allow_tools: false,
  allowed_tools: [],
  allow_mcp: false,
  allowed_mcp_transports: [],
  allow_tasks: false,
  max_cron_jobs: 0,
  min_cron_interval_minutes: 0,
  allow_task_run_now: false,
  allow_task_tools: false,
  task_timeout_seconds: 0,
  file_upload_limit_mb: 0,
  token_quota_monthly: null,
  advanced_config_enabled: false,
};

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => String(item).trim())
    .filter((item) => item.length > 0);
}

function normalizeNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

function normalizeNullableNumber(value: unknown, fallback: number | null): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  return normalizeNumber(value, fallback ?? 0);
}

export function policyToForm(policy: TenantPolicy): PolicyFormValues {
  return {
    ...policy,
    allowed_models: [...policy.allowed_models],
    allowed_tools: [...policy.allowed_tools],
    allowed_mcp_transports: [...policy.allowed_mcp_transports],
  };
}

export function formToPolicy(
  values: Partial<PolicyFormValues>,
  previousPolicy?: TenantPolicy,
): TenantPolicy {
  const base = previousPolicy ?? emptyPolicy;

  return {
    policy_id: values.policy_id?.trim() || base.policy_id,
    display_name: values.display_name?.trim() || base.display_name,
    allow_model_switch:
      values.allow_model_switch ?? base.allow_model_switch,
    allowed_models: normalizeStringList(
      values.allowed_models ?? base.allowed_models,
    ),
    allow_skill_create:
      values.allow_skill_create ?? base.allow_skill_create,
    allow_skill_upload_zip:
      values.allow_skill_upload_zip ?? base.allow_skill_upload_zip,
    allow_skill_hub_import:
      values.allow_skill_hub_import ?? base.allow_skill_hub_import,
    allow_tools: values.allow_tools ?? base.allow_tools,
    allowed_tools: normalizeStringList(values.allowed_tools ?? base.allowed_tools),
    allow_mcp: values.allow_mcp ?? base.allow_mcp,
    allowed_mcp_transports: normalizeStringList(
      values.allowed_mcp_transports ?? base.allowed_mcp_transports,
    ),
    allow_tasks: values.allow_tasks ?? base.allow_tasks,
    max_cron_jobs: normalizeNumber(values.max_cron_jobs, base.max_cron_jobs),
    min_cron_interval_minutes: normalizeNumber(
      values.min_cron_interval_minutes,
      base.min_cron_interval_minutes,
    ),
    allow_task_run_now:
      values.allow_task_run_now ?? base.allow_task_run_now,
    allow_task_tools: values.allow_task_tools ?? base.allow_task_tools,
    task_timeout_seconds: normalizeNumber(
      values.task_timeout_seconds,
      base.task_timeout_seconds,
    ),
    file_upload_limit_mb: normalizeNumber(
      values.file_upload_limit_mb,
      base.file_upload_limit_mb,
    ),
    token_quota_monthly: normalizeNullableNumber(
      values.token_quota_monthly,
      base.token_quota_monthly,
    ),
    advanced_config_enabled:
      values.advanced_config_enabled ?? base.advanced_config_enabled,
  };
}
