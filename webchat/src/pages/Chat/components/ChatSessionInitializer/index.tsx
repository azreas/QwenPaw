import React, { useEffect, useMemo, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useChatAnywhereSessionsState } from "@agentscope-ai/chat";
import { getWebchatChatId } from "../../../../utils/deployment";

interface ExtendedSession {
  id: string;
  sessionId?: string;
  realId?: string;
}

const legacyLocalSessionId = (sessionId: string | undefined): string | null => {
  if (!sessionId?.startsWith("webchat:")) return null;
  const parts = sessionId.split(":");
  return parts.length >= 3 ? parts[parts.length - 1] : null;
};

/**
 * URL chatId → context currentSessionId (one direction of bidirectional sync).
 *
 * Only reacts to URL or session list changes. currentSessionId is read via ref
 * to avoid triggering the effect when the context changes from the other direction
 * (context → URL via onSessionSelected), which would cause circular re-loads.
 */
const ChatSessionInitializer: React.FC = () => {
  const location = useLocation();
  const chatId = useMemo(() => {
    return getWebchatChatId(location.pathname);
  }, [location.pathname]);

  const { sessions, currentSessionId, setCurrentSessionId } =
    useChatAnywhereSessionsState();

  const currentSessionIdRef = useRef(currentSessionId);
  currentSessionIdRef.current = currentSessionId;

  useEffect(() => {
    // 如果 URL 是 /chat（无 ID），不执行任何操作，让 AgentScope 库自动选择
    if (!chatId) return;
    
    // 如果 URL 有 chatId，但会话列表还未加载，等待
    if (!Array.isArray(sessions) || !sessions.length) return;
    
    // 尝试通过多种方式匹配会话：
    // 1. 直接匹配 id（后端 UUID 或临时 ID）
    // 2. 匹配 sessionId（临时 ID）
    // 3. 匹配 realId（后端 UUID）
    const matching = sessions.find((s) => {
      const ext = s as ExtendedSession;
      return s.id === chatId || 
             ext.sessionId === chatId || 
             ext.realId === chatId ||
             legacyLocalSessionId(ext.sessionId) === chatId;
    });
    
    if (matching && currentSessionIdRef.current !== matching.id) {
      setCurrentSessionId(matching.id);
    }
    // Intentionally exclude currentSessionId from deps: only react to URL / session list changes.
    // currentSessionId is read via ref to avoid circular triggers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId, sessions, setCurrentSessionId]);

  return null;
};

export default ChatSessionInitializer;
