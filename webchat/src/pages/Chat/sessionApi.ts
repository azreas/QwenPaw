import { apiRequest } from "../../api/config";

export interface Session {
  id: string;
  session_id: string;
  name: string;
  user_id: string;
  channel: string;
  created_at: string;
  updated_at: string;
}

export interface ChatHistory {
  session_id: string;
  messages: Array<{
    role: string;
    content: string;
    timestamp: string;
  }>;
}

type SessionIdCallback = ((tempId: string, realId: string) => void) | null;
type SessionCallback = ((sessionId: string) => void) | null;
type SessionSelectedCallback = ((sessionId: string, realId: string) => void) | null;

const sessionApi = {
  onSessionIdResolved: null as SessionIdCallback,
  onSessionRemoved: null as SessionCallback,
  onSessionSelected: null as SessionSelectedCallback,
  onSessionCreated: null as SessionCallback,

  listSessions: async (params?: { user_id?: string; channel?: string; agent_id?: string }): Promise<Session[]> => {
    const searchParams = new URLSearchParams();
    if (params?.user_id) searchParams.append("user_id", params.user_id);
    if (params?.channel) searchParams.append("channel", params.channel);
    if (params?.agent_id) searchParams.append("agent_id", params.agent_id);
    const query = searchParams.toString();
    const response = await apiRequest<{ sessions: Session[] }>(`/webchat/sessions${query ? `?${query}` : ""}`);
    return response.sessions || [];
  },

  // 别名：兼容 @agentscope-ai/chat 组件的 API 名称
  getSessionList: async (params?: { user_id?: string; channel?: string }): Promise<Session[]> => {
    return sessionApi.listSessions(params);
  },

  getSession: async (sessionId: string): Promise<ChatHistory> => {
    return apiRequest<ChatHistory>(`/webchat/sessions/${encodeURIComponent(sessionId)}`);
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await apiRequest(`/webchat/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
  },

  createSession: async (session?: Partial<Session>): Promise<Session> => {
    return apiRequest<Session>("/webchat/sessions", {
      method: "POST",
      body: JSON.stringify(session || {}),
    });
  },

  updateSession: async (sessionIdOrSession: string | Partial<Session>, session?: Partial<Session>): Promise<Session> => {
    let actualSessionId: string;
    let actualSession: Partial<Session>;
    
    // 兼容两种调用方式：
    // 1. updateSession(sessionObject) - 从session.id获取sessionId
    // 2. updateSession(sessionId, sessionObject) - 直接传入sessionId
    if (typeof sessionIdOrSession === 'string') {
      actualSessionId = sessionIdOrSession;
      actualSession = session || {};
    } else {
      // sessionIdOrSession 是 session 对象
      actualSessionId = sessionIdOrSession.id || sessionIdOrSession.session_id || '';
      actualSession = sessionIdOrSession;
    }
    
    if (!actualSessionId) {
      console.error('updateSession: sessionId is missing', actualSession);
      throw new Error('Session ID is required');
    }
    
    return apiRequest<Session>(`/webchat/sessions/${encodeURIComponent(actualSessionId)}`, {
      method: "PUT",
      body: JSON.stringify(actualSession),
    });
  },
};

export default sessionApi;
