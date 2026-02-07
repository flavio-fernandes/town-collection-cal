import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const apiPaths = [
  "/town.ics",
  "/resolve",
  "/version",
  "/healthz",
  "/debug",
  "/streets",
];

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_DEV_PROXY_TARGET;
  const configuredBasePath = env.VITE_BASE_PATH?.trim();
  const base = configuredBasePath
    ? configuredBasePath.endsWith("/")
      ? configuredBasePath
      : `${configuredBasePath}/`
    : "/";

  return {
    base,
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: proxyTarget
        ? Object.fromEntries(apiPaths.map((path) => [path, proxyTarget]))
        : undefined,
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test-setup.ts"],
      include: ["src/**/*.test.ts"],
      exclude: ["tests/e2e/**"],
    },
  };
});
