const exactPathToKey: Record<string, string> = {
  "/chat": "chat",
  "/channels": "channels",
  "/sessions": "sessions",
  "/inbox": "inbox",
  "/cron-jobs": "cron-jobs",
  "/heartbeat": "heartbeat",
  "/platform": "platform",
  "/platform/policies": "platform-policies",
  "/platform/users": "platform-users",
  "/wecom-tenants": "wecom-tenant-management",
  "/wecom-tenants/monitoring": "wecom-tenant-monitoring",
  "/skills": "skills",
  "/skill-pool": "skill-pool",
  "/tools": "tools",
  "/mcp": "mcp",
  "/acp": "acp",
  "/workspace": "workspace",
  "/agents": "agents",
  "/models": "models",
  "/environments": "environments",
  "/agent-config": "agent-config",
  "/security": "security",
  "/token-usage": "token-usage",
  "/agent-stats": "agent-stats",
  "/voice-transcription": "voice-transcription",
  "/debug": "debug",
  "/backups": "backups",
  "/plugin-manager": "plugin-manager",
};

export function resolveStaticSelectedKey(pathname: string): string {
  if (pathname.startsWith("/wecom-tenants/monitoring")) {
    return "wecom-tenant-monitoring";
  }
  return exactPathToKey[pathname] || "";
}
