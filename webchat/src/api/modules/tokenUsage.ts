import { apiRequest } from "../config";

export interface TokenUsageStats {
  provider_id?: string;
  model?: string;
  prompt_tokens: number;
  completion_tokens: number;
  call_count: number;
}

export interface TokenUsageSummary {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_calls: number;
  by_model: Record<string, TokenUsageStats>;
  by_date: Record<string, TokenUsageStats>;
}

export interface GetTokenUsageParams {
  start_date: string;
  end_date: string;
}

function buildQuery(params: GetTokenUsageParams): string {
  const search = new URLSearchParams({
    start_date: params.start_date,
    end_date: params.end_date,
  });
  return `?${search.toString()}`;
}

export const tokenUsageApi = {
  getTokenUsage: async (params: GetTokenUsageParams): Promise<TokenUsageSummary> => {
    return apiRequest<TokenUsageSummary>(
      `/webchat/token-usage${buildQuery(params)}`
    );
  },
};
