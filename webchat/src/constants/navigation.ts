// Navigation constants for route-based sidebar
import { webchatPath } from "../utils/deployment";

export const KEY_TO_PATH: Record<string, string> = {
  chat: webchatPath("/chat"),
  files: webchatPath("/config/files"),
  skills: webchatPath("/config/skills"),
  tools: webchatPath("/config/tools"),
  mcp: webchatPath("/config/mcp"),
  agentConfig: webchatPath("/config/agent-config"),
  tasks: webchatPath("/my/tasks"),
  messages: webchatPath("/my/messages"),
  shortcuts: webchatPath("/my/shortcuts"),
  tokenUsage: webchatPath("/system/token-usage"),
};

export const PATH_TO_KEY: Record<string, string> = {
  [webchatPath("/chat")]: "chat",
  [webchatPath("/config/files")]: "files",
  [webchatPath("/config/skills")]: "skills",
  [webchatPath("/config/tools")]: "tools",
  [webchatPath("/config/mcp")]: "mcp",
  [webchatPath("/config/agent-config")]: "agentConfig",
  [webchatPath("/my/tasks")]: "tasks",
  [webchatPath("/my/messages")]: "messages",
  [webchatPath("/my/shortcuts")]: "shortcuts",
  [webchatPath("/system/token-usage")]: "tokenUsage",
};
