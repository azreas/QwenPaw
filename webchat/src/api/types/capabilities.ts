export interface MemberCapabilities {
  chat: boolean;
  sessions: boolean;
  files: boolean;
  skills: boolean;
  skill_create: boolean;
  skill_upload_zip: boolean;
  skill_hub_import: boolean;
  tools: boolean;
  model_switch: boolean;
  mcp: boolean;
  tasks: boolean;
  task_run_now: boolean;
  usage: boolean;
  advanced_config: boolean;
  platform_ops: boolean;
}

export interface MemberCapabilityLimits {
  allowed_models: string[];
  allowed_tools: string[];
  allowed_mcp_transports: string[];
  max_cron_jobs: number;
  min_cron_interval_minutes: number;
  task_timeout_seconds: number;
  file_upload_limit_mb: number;
  token_quota_monthly: number | null;
}

export interface WebchatCapabilitiesResponse {
  tenant_id: string;
  agent_id: string;
  policy_id: string;
  capabilities: MemberCapabilities;
  limits: MemberCapabilityLimits;
}
