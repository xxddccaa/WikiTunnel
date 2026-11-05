import { defineConfig } from "@playwright/test";

const testPort = 18765;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  timeout: 30_000,
  reporter: "line",
  use: {
    baseURL: `http://127.0.0.1:${testPort}`,
    channel: "chrome",
    headless: true,
    viewport: { width: 1500, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      `cd .. && AUTOSSH_DESK_NO_BROWSER=1 AUTOSSH_DESK_MONITOR_INTERVAL=3600 AUTOSSH_DESK_PORT=${testPort} AUTOSSH_DESK_DATA_DIR=/tmp/autossh-desk-playwright-${process.pid} .venv/bin/python app.py`,
    url: `http://127.0.0.1:${testPort}/api/health`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});

