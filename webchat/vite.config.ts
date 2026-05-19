import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

function normalizePublicBase(value: string | undefined): string {
  const raw = (value || "/webchat/").trim();
  if (!raw) return "/webchat/";
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
  const publicBase = normalizePublicBase(env.VITE_PUBLIC_BASE);
  const apiBaseUrl = env.VITE_API_BASE_URL ?? "";
  const routerBasename = env.VITE_ROUTER_BASENAME ?? "";
  const webchatRoutePrefix = env.VITE_WEBCHAT_ROUTE_PREFIX ?? "/webchat";

  return {
    plugins: [react()],
    base: publicBase,
    define: {
      VITE_API_BASE_URL: JSON.stringify(apiBaseUrl),
      VITE_ROUTER_BASENAME: JSON.stringify(routerBasename),
      VITE_WEBCHAT_ROUTE_PREFIX: JSON.stringify(webchatRoutePrefix),
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    css: {
      modules: {
        localsConvention: "camelCase",
      },
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5174,
      strictPort: false,
      allowedHosts: true,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8088",
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: false,
    },
    test: {
      globals: true,
      environment: "jsdom",
      exclude: [
        "**/node_modules/**",
        "**/dist/**",
        // 旧测试用 node:test，与 vitest 不兼容，待迁移
        "**/csrf.test.ts",
        "**/errors.test.ts",
      ],
    },
  };
});
