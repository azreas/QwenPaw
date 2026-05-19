declare const VITE_ROUTER_BASENAME: string;
declare const VITE_WEBCHAT_ROUTE_PREFIX: string;

const DEFAULT_WEBCHAT_ROUTE_PREFIX = "/webchat";

function normalizePathPrefix(value: string | undefined, fallback = ""): string {
  const raw = (value || fallback).trim();
  if (!raw || raw === "/") return "";
  const withLeadingSlash = raw.startsWith("/") ? raw : `/${raw}`;
  return withLeadingSlash.replace(/\/+$/, "");
}

function getCurrentPathname(): string {
  return typeof window !== "undefined" ? window.location.pathname || "/" : "/";
}

function inferRouterBasename(pathname: string, routePrefix: string): string {
  const normalizedPathname = normalizePathPrefix(pathname) || "/";
  const normalizedRoutePrefix = normalizePathPrefix(routePrefix, DEFAULT_WEBCHAT_ROUTE_PREFIX);
  if (!normalizedRoutePrefix) return "";

  if (normalizedPathname === normalizedRoutePrefix) return "";
  if (normalizedPathname.startsWith(`${normalizedRoutePrefix}/`)) return "";

  if (normalizedPathname.endsWith(normalizedRoutePrefix)) {
    return normalizePathPrefix(
      normalizedPathname.slice(0, -normalizedRoutePrefix.length),
    );
  }

  const marker = `${normalizedRoutePrefix}/`;
  const markerIndex = normalizedPathname.indexOf(marker);
  if (markerIndex <= 0) return "";
  return normalizePathPrefix(normalizedPathname.slice(0, markerIndex));
}

function stripLeadingPrefix(value: string, prefix: string): string {
  if (!prefix) return value;
  if (value === prefix) return "";
  if (value.startsWith(`${prefix}/`)) {
    return normalizePathPrefix(value.slice(prefix.length));
  }
  return value;
}

const configuredRouterBasename = normalizePathPrefix(
  typeof VITE_ROUTER_BASENAME === "string" ? VITE_ROUTER_BASENAME : "",
);

const configuredWebchatRoutePrefix =
  normalizePathPrefix(
    typeof VITE_WEBCHAT_ROUTE_PREFIX === "string"
      ? VITE_WEBCHAT_ROUTE_PREFIX
      : "",
    DEFAULT_WEBCHAT_ROUTE_PREFIX,
  ) || DEFAULT_WEBCHAT_ROUTE_PREFIX;
const routerBasenameFromRoutePrefix = inferRouterBasename(
  configuredWebchatRoutePrefix,
  DEFAULT_WEBCHAT_ROUTE_PREFIX,
);

export const routerBasename =
  configuredRouterBasename ||
  routerBasenameFromRoutePrefix ||
  inferRouterBasename(getCurrentPathname(), configuredWebchatRoutePrefix);

export const webchatRoutePrefix =
  stripLeadingPrefix(configuredWebchatRoutePrefix, routerBasename) ||
  DEFAULT_WEBCHAT_ROUTE_PREFIX;

export function stripRouterBasename(pathname: string): string {
  if (!routerBasename) return pathname || "/";
  if (pathname === routerBasename) return "/";
  if (pathname.startsWith(`${routerBasename}/`)) {
    return pathname.slice(routerBasename.length) || "/";
  }
  return pathname || "/";
}

export function webchatPath(path = ""): string {
  if (!path) return webchatRoutePrefix;
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${webchatRoutePrefix}${suffix}`;
}

export function getWebchatChatId(pathname: string): string | undefined {
  const normalizedPath = stripRouterBasename(pathname);
  const prefix = `${webchatRoutePrefix}/chat/`;
  if (!normalizedPath.startsWith(prefix)) return undefined;
  return normalizedPath.slice(prefix.length);
}
