import { apiRequest } from "../config";

export interface MCPClientInfo {
  key: string;
  name: string;
  description?: string;
  enabled: boolean;
  transport: "stdio" | "streamable_http" | "sse";
  url?: string;
  headers?: Record<string, string>;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
  tools?: MCPToolInfo[];
  isConnected?: boolean;
  error?: string;
}

export interface MCPToolInfo {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

export interface MCPClientCreateRequest {
  key: string;
  name?: string;
  description?: string;
  enabled?: boolean;
  transport: "stdio" | "streamable_http" | "sse";
  url?: string;
  headers?: Record<string, string>;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
}

export interface MCPClientUpdateRequest {
  name?: string;
  description?: string;
  enabled?: boolean;
  transport?: "stdio" | "streamable_http" | "sse";
  url?: string;
  headers?: Record<string, string>;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
}

export const mcpApi = {
  listMCPClients: () => apiRequest<MCPClientInfo[]>("/mcp"),

  getMCPClient: (clientKey: string) =>
    apiRequest<MCPClientInfo>(`/mcp/${encodeURIComponent(clientKey)}`),

  createMCPClient: (body: MCPClientCreateRequest) =>
    apiRequest<MCPClientInfo>("/mcp", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateMCPClient: (clientKey: string, body: MCPClientUpdateRequest) =>
    apiRequest<MCPClientInfo>(`/mcp/${encodeURIComponent(clientKey)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  toggleMCPClient: (clientKey: string) =>
    apiRequest<MCPClientInfo>(`/mcp/${encodeURIComponent(clientKey)}/toggle`, {
      method: "PATCH",
    }),

  deleteMCPClient: (clientKey: string) =>
    apiRequest<{ message: string }>(`/mcp/${encodeURIComponent(clientKey)}`, {
      method: "DELETE",
    }),

  listMCPTools: (clientKey: string) =>
    apiRequest<MCPToolInfo[]>(`/mcp/${encodeURIComponent(clientKey)}/tools`),
};
