import { apiRequest } from "../config";

export interface AgentsRunningConfig {
  max_iters?: number;
  auto_continue_on_text_only?: boolean;
  memory_manager_backend?: string;
  max_input_length?: number;
  llm_retry_enabled?: boolean;
  llm_max_retries?: number;
  llm_backoff_base?: number;
  llm_backoff_cap?: number;
  llm_max_concurrent?: number;
  llm_max_qpm?: number;
  llm_rate_limit_pause?: number;
  llm_rate_limit_jitter?: number;
  llm_acquire_timeout?: number;
  context_compact?: {
    context_compact_enabled?: boolean;
    token_count_estimate_divisor?: number;
    memory_compact_ratio?: number;
    memory_reserve_ratio?: number;
    compact_with_thinking_block?: boolean;
  };
  tool_result_compact?: {
    enabled?: boolean;
    recent_n?: number;
    old_max_bytes?: number;
    recent_max_bytes?: number;
    retention_days?: number;
  };
  memory_summary?: {
    memory_summary_enabled?: boolean;
    dream_cron?: string;
    force_memory_search?: boolean;
    force_max_results?: number;
    force_min_score?: number;
    rebuild_memory_index_on_start?: boolean;
  };
  embedding_config?: {
    base_url?: string;
    model_name?: string;
    api_key?: string;
    dimensions?: number;
    enable_cache?: boolean;
    max_cache_size?: number;
    max_input_length?: number;
    max_batch_size?: number;
  };
}

export const agentConfigApi = {
  getRunningConfig: async (): Promise<AgentsRunningConfig> => {
    return apiRequest<AgentsRunningConfig>("/webchat/agent/running-config");
  },

  updateRunningConfig: async (config: AgentsRunningConfig): Promise<AgentsRunningConfig> => {
    return apiRequest<AgentsRunningConfig>("/webchat/agent/running-config", {
      method: "PUT",
      body: JSON.stringify(config),
    });
  },

  getLanguage: async (): Promise<{ language: string }> => {
    return apiRequest<{ language: string }>("/webchat/agent/language");
  },

  updateLanguage: async (language: string): Promise<{ language: string; copied_files: string[] }> => {
    return apiRequest<{ language: string; copied_files: string[] }>("/webchat/agent/language", {
      method: "PUT",
      body: JSON.stringify({ language }),
    });
  },

  getTimezone: async (): Promise<{ timezone: string }> => {
    return apiRequest<{ timezone: string }>("/webchat/agent/user-timezone");
  },

  updateTimezone: async (timezone: string): Promise<{ timezone: string }> => {
    return apiRequest<{ timezone: string }>("/webchat/agent/user-timezone", {
      method: "PUT",
      body: JSON.stringify({ timezone }),
    });
  },
};
