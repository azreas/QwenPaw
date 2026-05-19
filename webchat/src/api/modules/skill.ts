import { apiRequest, getApiUrl, getAuthHeaders } from "../config";

export interface SkillSpec {
  name: string;
  description: string;
  content: string;
  enabled: boolean;
  source?: string;
  channels?: string[];
  tags?: string[];
  config?: Record<string, unknown>;
  last_updated?: string;
  emoji?: string;
}

export const skillApi = {
  listSkills: () =>
    apiRequest<{ skills: SkillSpec[] }>("/agent/skills").then((res) => res.skills || []),

  refreshSkills: () =>
    apiRequest<{ skills: SkillSpec[] }>("/agent/skills/refresh", { method: "POST" }).then(
      (res) => res.skills || []
    ),

  createSkill: (
    skillName: string,
    content: string,
    config?: Record<string, unknown>,
    enable?: boolean
  ) =>
    apiRequest<{ created: boolean; name: string }>("/agent/skills", {
      method: "POST",
      body: JSON.stringify({
        name: skillName,
        content,
        config,
        enable,
      }),
    }),

  saveSkill: (payload: {
    name: string;
    content: string;
    source_name?: string;
    config?: Record<string, unknown>;
    overwrite?: boolean;
  }) =>
    apiRequest<{
      success: boolean;
      mode: "edit" | "rename" | "noop";
      name: string;
    }>("/agent/skills/save", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  enableSkill: (skillName: string) =>
    apiRequest<{ enabled: boolean }>(
      `/agent/skills/${encodeURIComponent(skillName)}`,
      {
        method: "PUT",
        body: JSON.stringify({ enabled: true }),
      }
    ),

  disableSkill: (skillName: string) =>
    apiRequest<{ disabled: boolean }>(
      `/agent/skills/${encodeURIComponent(skillName)}`,
      {
        method: "PUT",
        body: JSON.stringify({ enabled: false }),
      }
    ),

  deleteSkill: (skillName: string) =>
    apiRequest<{ deleted: boolean }>(
      `/agent/skills/${encodeURIComponent(skillName)}`,
      {
        method: "DELETE",
      }
    ),

  batchDeleteSkills: (skillNames: string[]) =>
    apiRequest<{ results: Record<string, { success: boolean; reason?: string }> }>(
      "/agent/skills/batch-delete",
      {
        method: "POST",
        body: JSON.stringify({ skills: skillNames }),
      }
    ),

  uploadSkill: async (
    file: File,
    options?: {
      enable?: boolean;
      overwrite?: boolean;
      target_name?: string;
      rename_map?: Record<string, string>;
    }
  ): Promise<{
    imported: string[];
    count: number;
    enabled: boolean;
    conflicts?: Array<{
      reason: string;
      skill_name: string;
      suggested_name: string;
    }>;
  }> => {
    const formData = new FormData();
    formData.append("file", file);

    const params = new URLSearchParams();
    if (options?.enable !== undefined) {
      params.set("enable", String(options.enable));
    }
    if (options?.overwrite !== undefined) {
      params.set("overwrite", String(options.overwrite));
    }
    if (options?.target_name) {
      params.set("target_name", options.target_name);
    }
    if (options?.rename_map && Object.keys(options.rename_map).length) {
      params.set("rename_map", JSON.stringify(options.rename_map));
    }
    const qs = params.toString();
    const url = getApiUrl(`/agent/skills/upload-zip${qs ? `?${qs}` : ""}`);

    const response = await fetch(url, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    return await response.json();
  },

  updateSkillChannels: (skillName: string, channels: string[]) =>
    apiRequest<{ updated: boolean; channels: string[] }>(
      `/agent/skills/${encodeURIComponent(skillName)}/channels`,
      {
        method: "PUT",
        body: JSON.stringify({ channels }),
      }
    ),

  updateSkillTags: (skillName: string, tags: string[]) =>
    apiRequest<{ updated: boolean; tags: string[] }>(
      `/agent/skills/${encodeURIComponent(skillName)}/tags`,
      {
        method: "PUT",
        body: JSON.stringify({ tags }),
      }
    ),

  getSkillConfig: (skillName: string) =>
    apiRequest<{ config: Record<string, unknown> }>(
      `/agent/skills/${encodeURIComponent(skillName)}/config`
    ),

  updateSkillConfig: (skillName: string, config: Record<string, unknown>) =>
    apiRequest<{ updated: boolean }>(
      `/agent/skills/${encodeURIComponent(skillName)}/config`,
      {
        method: "PUT",
        body: JSON.stringify({ config }),
      }
    ),

  getSkillFile: (skillName: string, filePath: string) =>
    apiRequest<{ content: string }>(
      `/agent/skills/${encodeURIComponent(skillName)}/files/${encodeURIComponent(filePath)}`
    ),
};
