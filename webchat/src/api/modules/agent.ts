import { apiRequest, getAbsoluteApiUrl, getAuthHeaders } from "../config";

export interface Tool {
  name: string;
  enabled: boolean;
  description: string;
  display_to_user: boolean;
}

export interface MCPClient {
  name: string;
  display_name: string;
  enabled: boolean;
  description: string;
  transport: string;
}

export interface Skill {
  name: string;
  enabled: boolean;
  description: string;
  source: string;
}

export interface SkillSpec {
  name: string;
  description: string;
  content: string;
  enabled: boolean;
  source?: string;
  installed?: boolean;
  installable?: boolean;
  channels?: string[];
  tags?: string[];
  config?: Record<string, unknown>;
  last_updated?: string;
  emoji?: string;
}

export interface SkillUploadResult {
  imported: string[];
  renamed: Record<string, string>;
  conflicts: string[];
  count: number;
}

export interface PoolSkillSpec {
  name: string;
  description: string;
  source: string;
  enabled: boolean;
  tags: string[];
  protected: boolean;
  version_text: string;
  sync_status: string;
  last_updated: string;
}

export interface SkillCreateRequest {
  name: string;
  content: string;
  config?: Record<string, unknown>;
  enable?: boolean;
}

export interface FileItem {
  name: string;
  type: string;
  size: number;
  lines: number;
  enabled?: boolean;
}

export interface AgentConfig {
  agent_id: string;
  name: string;
  description: string;
  model_id: string;
  system_prompt: string;
  max_turns: number;
  temperature: number;
  enable_memory: boolean;
  language: string;
  tools: Tool[];
  mcp_clients: MCPClient[];
  skills: Skill[];
  files: FileItem[];
  workspace_dir: string;
}

export interface WorkspaceFile {
  name: string;
  path: string;
  content: string;
  enabled: boolean;
}

export interface MarkdownFileInfo {
  filename: string;
  path: string;
  size: number;
  created_time?: string;
  modified_time?: string;
}

export const agentApi = {
  getConfig: async (): Promise<AgentConfig> => {
    return apiRequest<AgentConfig>("/webchat/agent/config");
  },

  updateConfig: async (config: Partial<AgentConfig>): Promise<void> => {
    await apiRequest("/webchat/agent/config", {
      method: "PUT",
      body: JSON.stringify(config),
    });
  },

  getFiles: async (): Promise<WorkspaceFile[]> => {
    return apiRequest<WorkspaceFile[]>("/webchat/agent/files");
  },

  getFileContent: async (filename: string): Promise<string> => {
    const response = await apiRequest<{ content: string }>(
      `/webchat/agent/files/${encodeURIComponent(filename)}`
    );
    return response.content;
  },

  updateFileContent: async (
    filename: string,
    content: string
  ): Promise<void> => {
    await apiRequest(`/webchat/agent/files/${encodeURIComponent(filename)}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    });
  },

  toggleFileEnabled: async (
    filename: string,
    enabled: boolean
  ): Promise<void> => {
    await apiRequest(
      `/webchat/agent/files/${encodeURIComponent(filename)}/enabled`,
      {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      }
    );
  },

  toggleTool: async (toolName: string, enabled: boolean): Promise<void> => {
    await apiRequest(`/webchat/agent/tools/${encodeURIComponent(toolName)}`, {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    });
  },

  toggleMCP: async (clientName: string, enabled: boolean): Promise<void> => {
    await apiRequest(`/webchat/agent/mcp/${encodeURIComponent(clientName)}`, {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    });
  },

  toggleSkill: async (skillName: string, enabled: boolean): Promise<void> => {
    await apiRequest(`/webchat/agent/skills/${encodeURIComponent(skillName)}`, {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    });
  },

  // 新增完整技能管理API
  listSkills: async (): Promise<SkillSpec[]> => {
    const response = await apiRequest<{ skills: SkillSpec[] }>("/webchat/agent/skills");
    return response.skills || [];
  },

  getSkillContent: async (skillName: string): Promise<{ name: string; content: string }> => {
    return apiRequest(`/webchat/agent/skills/${encodeURIComponent(skillName)}/content`);
  },

  createSkill: async (data: SkillCreateRequest): Promise<{ success: boolean; name: string }> => {
    return apiRequest("/webchat/agent/skills", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateSkill: async (skillName: string, content: string, config?: Record<string, unknown>): Promise<void> => {
    await apiRequest(`/webchat/agent/skills/${encodeURIComponent(skillName)}`, {
      method: "PUT",
      body: JSON.stringify({ content, config }),
    });
  },

  deleteSkill: async (skillName: string): Promise<void> => {
    await apiRequest(`/webchat/agent/skills/${encodeURIComponent(skillName)}`, {
      method: "DELETE",
    });
  },

  batchDeleteSkills: async (skillNames: string[]): Promise<{ results: Record<string, { success: boolean; reason?: string }> }> => {
    return apiRequest("/webchat/agent/skills/batch-delete", {
      method: "POST",
      body: JSON.stringify({ skills: skillNames }),
    });
  },

  getSkillConfig: async (skillName: string): Promise<{ config: Record<string, unknown> }> => {
    return apiRequest(`/webchat/agent/skills/${encodeURIComponent(skillName)}/config`);
  },

  updateSkillConfig: async (skillName: string, config: Record<string, unknown>): Promise<void> => {
    await apiRequest(`/webchat/agent/skills/${encodeURIComponent(skillName)}/config`, {
      method: "PUT",
      body: JSON.stringify({ config }),
    });
  },

  updateSkillChannels: async (skillName: string, channels: string[]): Promise<void> => {
    await apiRequest(`/webchat/agent/skills/${encodeURIComponent(skillName)}/channels`, {
      method: "PUT",
      body: JSON.stringify({ channels }),
    });
  },

  updateSkillTags: async (skillName: string, tags: string[]): Promise<void> => {
    await apiRequest(`/webchat/agent/skills/${encodeURIComponent(skillName)}/tags`, {
      method: "PUT",
      body: JSON.stringify({ tags }),
    });
  },

  // 技能池相关API
  listSkillPoolSkills: async (): Promise<PoolSkillSpec[]> => {
    const response = await apiRequest<{ skills: PoolSkillSpec[] }>("/webchat/agent/skill-pool/skills");
    return response.skills || [];
  },

  uploadSkillToPool: async (payload: {
    skill_name: string;
    new_name?: string;
    overwrite?: boolean;
  }): Promise<{ success: boolean; name: string }> => {
    return apiRequest("/webchat/agent/skill-pool/upload", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  downloadSkillFromPool: async (payload: {
    skill_name: string;
    target_name?: string;
    overwrite?: boolean;
  }): Promise<{ success: boolean; name: string }> => {
    return apiRequest("/webchat/agent/skill-pool/download", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  importUploadedSkill: async (payload: {
    skill_name: string;
    overwrite?: boolean;
  }): Promise<{ success: boolean; name: string; enabled?: boolean }> => {
    return apiRequest("/webchat/agent/skills/install-uploaded", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  uploadSkillZip: async (
    file: File,
    enable?: boolean,
    overwrite?: boolean,
    target_name?: string,
    rename_map?: string
  ): Promise<SkillUploadResult> => {
    const formData = new FormData();
    formData.append("file", file);
    if (enable !== undefined) formData.append("enable", String(enable));
    if (overwrite !== undefined) formData.append("overwrite", String(overwrite));
    if (target_name) formData.append("target_name", target_name);
    if (rename_map) formData.append("rename_map", rename_map);

    const response = await fetch(
      getAbsoluteApiUrl("/webchat/agent/skills/upload-zip"),
      {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  },

  importSkillFromHub: async (payload: {
    bundle_url: string;
    target_name?: string;
    overwrite?: boolean;
  }): Promise<{ installed: boolean; name: string; enabled: boolean; source_url: string }> => {
    return apiRequest("/webchat/agent/skills/import-hub", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // 文件管理API - 与console保持一致
  listAgentFiles: async (): Promise<MarkdownFileInfo[]> => {
    return apiRequest<MarkdownFileInfo[]>("/webchat/agent/files");
  },

  getSystemPromptFiles: async (): Promise<string[]> => {
    return apiRequest<string[]>("/webchat/agent/system-prompt-files");
  },

  updateSystemPromptFiles: async (files: string[]): Promise<void> => {
    await apiRequest("/webchat/agent/system-prompt-files", {
      method: "PUT",
      body: JSON.stringify({ system_prompt_files: files }),
    });
  },
};
