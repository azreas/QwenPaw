import { apiRequest, getApiUrl, getAuthHeaders } from "../config";

export interface MdFileInfo {
  filename: string;
  path: string;
  size: number;
  created_time: string;
  modified_time: string;
  lines?: number;
}

export interface MdFileContent {
  content: string;
}

export interface DailyMemoryFile extends MdFileInfo {
  date: string;
  updated_at: number;
}

export interface WorkspaceDownloadResult {
  blob: Blob;
  filename: string;
}

export interface WorkspaceEntry {
  name: string;
  type: "file" | "dir";
  size: number;
  deletable: boolean;
}

export interface WorkspaceDir {
  path: string;
  entries: WorkspaceEntry[];
}

function generateFallbackFilename(): string {
  const agentId = localStorage.getItem("webchat_agent_id") || "default";
  const now = new Date();
  const timestamp = now
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\..+/, "")
    .replace("T", "_")
    .slice(0, 15);
  return `qwenpaw_workspace_${agentId}_${timestamp}.zip`;
}

export const workspaceApi = {
  /** 列出工作区目录内容 */
  listFiles: (path?: string) => {
    const params = new URLSearchParams();
    if (path) params.set("path", path);
    return apiRequest<WorkspaceDir>(
      `/webchat/agent/workspace/files?${params.toString()}`,
    );
  },

  loadFile: (fileName: string) =>
    apiRequest<MdFileContent>(`/webchat/agent/files/${encodeURIComponent(fileName)}`),

  saveFile: (fileName: string, content: string) =>
    apiRequest<Record<string, unknown>>(
      `/webchat/agent/files/${encodeURIComponent(fileName)}`,
      {
        method: "PUT",
        body: JSON.stringify({ content }),
      }
    ),

  downloadWorkspace: async (): Promise<WorkspaceDownloadResult> => {
    const response = await fetch(getApiUrl("/webchat/agent/workspace/download"), {
      method: "GET",
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error(
        `Workspace download failed: ${response.status} ${response.statusText}`
      );
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition");
    let filename: string;

    if (disposition) {
      const filenameMatch = disposition.match(/filename="(.+?)"/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      } else {
        filename = generateFallbackFilename();
      }
    } else {
      filename = generateFallbackFilename();
    }

    return { blob, filename };
  },

  uploadFile: async (
    file: File
  ): Promise<{ success: boolean; message: string }> => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(getApiUrl("/webchat/agent/workspace/upload"), {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Upload failed: ${response.status} ${response.statusText} - ${errorText}`
      );
    }

    return await response.json();
  },

  getSystemPromptFiles: () => apiRequest<string[]>("/webchat/agent/system-prompt-files").catch(() => []),

  setSystemPromptFiles: (files: string[]) =>
    apiRequest<string[]>("/webchat/agent/system-prompt-files", {
      method: "PUT",
      body: JSON.stringify(files),
    }).catch(() => ({ success: true })),

  /** 删除工作区文件 */
  deleteWorkspaceFile: (filePath: string) =>
    apiRequest<{ success: boolean }>(
      `/webchat/agent/workspace/files?path=${encodeURIComponent(filePath)}`,
      { method: "DELETE" },
    ),

  /** 上传文件到工作区指定路径 */
  uploadWorkspaceFile: async (
    file: File,
    uploadPath?: string,
  ): Promise<{ name: string; path: string; size: number }> => {
    const url =
      getApiUrl(
        `/webchat/agent/workspace/files/upload${uploadPath ? `?path=${encodeURIComponent(uploadPath)}` : ""}`,
      );
    const resp = await fetch(url, {
      method: "POST",
      headers: getAuthHeaders(),
      body: (() => {
        const fd = new FormData();
        fd.append("file", file);
        return fd;
      })(),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return resp.json();
  },

  // Daily memory management
  listDailyMemory: () =>
    apiRequest<MdFileInfo[]>("/webchat/agent/files").then((files) =>
      files
        .filter((f) => /^\d{4}-\d{2}-\d{2}\.md$/.test(f.filename))
        .map((file) => {
          const date = file.filename.replace(".md", "");
          return {
            ...file,
            date,
            updated_at: new Date(file.modified_time).getTime(),
          } as DailyMemoryFile;
        })
    ).catch(() => []),

  loadDailyMemory: (date: string) =>
    apiRequest<MdFileContent>(
      `/webchat/agent/files/${encodeURIComponent(date)}.md`
    ),

  saveDailyMemory: (date: string, content: string) =>
    apiRequest<Record<string, unknown>>(
      `/webchat/agent/files/${encodeURIComponent(date)}.md`,
      {
        method: "PUT",
        body: JSON.stringify({ content }),
      }
    ),
};
