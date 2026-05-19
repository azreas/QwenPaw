export interface TenantPolicy {
  policy_id: string;
  display_name: string;
  allow_model_switch: boolean;
  allowed_models: string[];
  allow_skill_create: boolean;
  allow_skill_upload_zip: boolean;
  allow_skill_hub_import: boolean;
  allow_tools: boolean;
  allowed_tools: string[];
  allow_mcp: boolean;
  allowed_mcp_transports: string[];
  allow_tasks: boolean;
  max_cron_jobs: number;
  min_cron_interval_minutes: number;
  allow_task_run_now: boolean;
  allow_task_tools: boolean;
  task_timeout_seconds: number;
  file_upload_limit_mb: number;
  token_quota_monthly: number | null;
  advanced_config_enabled: boolean;
}

export interface TenantRecord {
  tenant_id: string;
  display_name: string;
  agent_id: string;
  status: string;
  source: string;
  policy_id: string;
  template_id: string;
  created_at: string;
  updated_at: string;
}

export interface TenantTemplate {
  template_id: string;
  display_name: string;
  default_model: string | null;
  default_prompt_files: string[];
  default_skills: string[];
  default_tools: string[];
  default_task_templates: Record<string, unknown>[];
}

export interface TenantListResponse {
  tenants: TenantRecord[];
}

export interface PolicyListResponse {
  policies: TenantPolicy[];
}

export interface TemplateListResponse {
  templates: TenantTemplate[];
}

export interface DeleteResponse {
  deleted: boolean;
}
