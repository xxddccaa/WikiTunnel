import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  timeout: 30_000,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:8765",
    channel: "chrome",
    headless: true,
    viewport: { width: 1500, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      "cd .. && WIKITUNNEL_NO_BROWSER=1 WIKITUNNEL_DATA_DIR=/tmp/wikitunnel-playwright .venv/bin/python app.py",
    url: "http://127.0.0.1:8765/api/health",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});

