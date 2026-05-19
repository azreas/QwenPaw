import { apiRequest } from "../config";

export interface ToolInfo {
  name: string;
  enabled: boolean;
  description: string;
  async_execution: boolean;
  icon: string;
}

export const toolsApi = {
  listTools: () => apiRequest<ToolInfo[]>("/webchat/agent/tools"),

  toggleTool: (toolName: string) =>
    apiRequest<ToolInfo>(`/webchat/agent/tools/${encodeURIComponent(toolName)}/toggle`, {
      method: "PATCH",
    }),

  updateAsyncExecution: (toolName: string, asyncExecution: boolean) =>
    apiRequest<ToolInfo>(
      `/webchat/agent/tools/${encodeURIComponent(toolName)}/async-execution`,
      {
        method: "PATCH",
        body: JSON.stringify({ async_execution: asyncExecution }),
      }
    ),
};
