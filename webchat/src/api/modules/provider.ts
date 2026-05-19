import { apiRequest } from "../config";

export interface ModelInfo {
  id: string;
  name: string;
  description?: string;
  supports_multimodal?: boolean;
  supports_image?: boolean;
  supports_video?: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  description?: string;
  models?: ModelInfo[];
  extra_models?: ModelInfo[];
  base_url?: string;
  api_key?: string;
  require_api_key?: boolean;
  is_custom?: boolean;
}

export interface ActiveModelsInfo {
  active_llm?: {
    provider_id: string;
    model: string;
  };
}

export interface SetActiveLlmRequest {
  provider_id: string;
  model: string;
  scope?: string;
  agent_id?: string;
}

export interface GetActiveModelsRequest {
  scope?: string;
  agent_id?: string;
}

function buildActiveModelQuery(params?: GetActiveModelsRequest): string {
  if (!params?.scope && !params?.agent_id) {
    return "/webchat/active-models";
  }

  const searchParams = new URLSearchParams();
  if (params.scope) {
    searchParams.set("scope", params.scope);
  }
  if (params.agent_id) {
    searchParams.set("agent_id", params.agent_id);
  }

  return `/webchat/active-models?${searchParams.toString()}`;
}

export const providerApi = {
  listProviders: () => apiRequest<ProviderInfo[]>("/webchat/providers"),

  getActiveModels: (params?: GetActiveModelsRequest) =>
    apiRequest<ActiveModelsInfo>(buildActiveModelQuery(params)),

  setActiveLlm: (body: SetActiveLlmRequest) =>
    apiRequest<void>("/webchat/active-models", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
};
