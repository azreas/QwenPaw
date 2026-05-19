import { useChatAnywhereSessionsState } from "@agentscope-ai/chat";
import { useTranslation } from "react-i18next";

export default function ChatHeaderTitle() {
  const { t } = useTranslation();
  const { currentSessionId, sessions } = useChatAnywhereSessionsState();

  const currentSession = Array.isArray(sessions) ? sessions.find((s) => s.id === currentSessionId) : undefined;
  const title = typeof currentSession?.name === 'string' ? currentSession.name : (currentSession?.name ? String(currentSession.name) : t("chat.newChat"));

  return <span className="chat-title">{title}</span>;
}