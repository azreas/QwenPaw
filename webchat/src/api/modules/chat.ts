import { getApiUrl, getAuthHeaders, apiRequest } from "../config";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  session_id?: string;
  messages?: ChatMessage[];
  reconnect?: boolean;
}

export async function streamChat(
  request: ChatRequest,
  onMessage: (data: string) => void,
  _onError: (error: Error) => void,
  signal?: AbortSignal
): Promise<void> {
  const url = getApiUrl("/webchat/chat");
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
  };

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      session_id: request.session_id || "",
      input: request.messages?.map((m) => ({
        role: m.role,
        content: [{ type: "text", text: m.content }],
      })) || [],
      reconnect: request.reconnect,
    }),
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data.trim()) {
            onMessage(data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function stopChat(chatId: string): Promise<void> {
  const url = getApiUrl(`/webchat/chat/stop?chat_id=${encodeURIComponent(chatId)}`);
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
  };

  const response = await fetch(url, {
    method: "POST",
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
}

export interface UploadResponse {
  url: string;
  file_name: string;
  size: number;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const url = getApiUrl("/webchat/upload");
  const headers = getAuthHeaders();

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Additional functions needed for compatibility with console
export interface ChatSpec {
  id: string;
  session_id: string;
  user_id: string;
  channel: string;
  name: string;
  status: string;
  created_at: string;
  meta?: Record<string, unknown>;
}

export interface ChatHistory {
  id: string;
  session_id: string;
  user_id: string;
  channel: string;
  name: string;
  messages: Array<{
    id: string;
    role: string;
    content: unknown;
    type?: string;
    sequence_number?: number;
  }>;
}

export interface ChatDeleteResponse {
  success: boolean;
}

export interface ChatUpdateRequest {
  name?: string;
  pinned?: boolean;
}

export interface Session {
  id: string;
  name: string;
  session_id: string;
  user_id: string;
  channel: string;
  messages: Array<{
    id: string;
    role: string;
    content: unknown;
    type?: string;
    sequence_number?: number;
  }>;
}

export const chatApi = {
  listChats: async (params?: { user_id?: string; channel?: string }): Promise<ChatSpec[]> => {
    const searchParams = new URLSearchParams();
    if (params?.user_id) searchParams.append("user_id", params.user_id);
    if (params?.channel) searchParams.append("channel", params.channel);
    
    // 首先获取当前用户的agent信息
    const userResponse = await apiRequest<{ agent_id: string; user_id: string; username: string }>("/webchat/me");
    const agentId = userResponse.agent_id;
    
    // 然后使用agent_id过滤聊天记录
    const response = await apiRequest<{ sessions: ChatSpec[] }>(`/webchat/sessions?agent_id=${encodeURIComponent(agentId)}`);
    return response.sessions || [];
  },

  getChat: async (chatId: string): Promise<ChatHistory> => {
    const response = await apiRequest<ChatHistory>(`/webchat/sessions/${encodeURIComponent(chatId)}`);
    return {
      id: response.id,
      session_id: response.session_id,
      user_id: response.user_id,
      channel: response.channel,
      name: response.name,
      messages: response.messages || [],
    };
  },

  updateChat: async (chatId: string, chat: ChatUpdateRequest): Promise<ChatSpec> => {
    const response = await apiRequest<ChatSpec>(`/webchat/sessions/${encodeURIComponent(chatId)}`, {
      method: "PUT",
      body: JSON.stringify(chat),
    });
    return response;
  },

  deleteChat: async (chatId: string): Promise<ChatDeleteResponse> => {
    await apiRequest(`/webchat/sessions/${encodeURIComponent(chatId)}`, {
      method: "DELETE",
    });
    return { success: true };
  },

  stopChat: async (chatId: string): Promise<void> => {
    await stopChat(chatId);
  },

  uploadFile: async (file: File): Promise<UploadResponse> => {
    return uploadFile(file);
  },
};