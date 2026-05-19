/// <reference types="vitest" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

function normalizePublicBase(value: string | undefined): string {
  const raw = (value || "/").trim();
  if (!raw) return "/";
  const withLeadingSlash =
    raw.startsWith("/") || /^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(raw)
      ? raw
      : `/${raw}`;
  return withLeadingSlash.endsWith("/")
    ? withLeadingSlash
    : `${withLeadingSlash}/`;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBaseUrl = env.VITE_API_BASE_URL ?? "";
  // 默认构建 base 为 /enterprise-admin/，匹配后端路由
  const publicBase = normalizePublicBase(env.VITE_PUBLIC_BASE ?? "/enterprise-admin/");
  const routerBasename = env.VITE_ROUTER_BASENAME ?? "/enterprise-admin";

  return {
    base: publicBase,
    define: {
      VITE_API_BASE_URL: JSON.stringify(apiBaseUrl),
      VITE_PUBLIC_BASE: JSON.stringify(publicBase),
      VITE_ROUTER_BASENAME: JSON.stringify(routerBasename),
      TOKEN: JSON.stringify(env.TOKEN || ""),
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5175,
      proxy: {
        "/api": {
          target: env.VITE_DEV_API_PROXY_TARGET ?? "http://127.0.0.1:8088",
          changeOrigin: true,
        },
        "/ready": {
          target: env.VITE_DEV_API_PROXY_TARGET ?? "http://127.0.0.1:8088",
          changeOrigin: true,
        },
      },
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      css: true,
      exclude: ["**/node_modules/**", "**/dist/**"],
    },
    build: {
      cssCodeSplit: true,
      sourcemap: mode !== "production",
      chunkSizeWarningLimit: 1000,
    },
  };
});
