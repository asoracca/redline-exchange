import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./research-tests",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8002",
    viewport: { width: 1440, height: 1200 },
  },
  webServer: {
    command: `cd .. && REDLINE_RESEARCH_DIR=/tmp/redline-research-browser-${process.pid} .venv/bin/python -m uvicorn research_copilot.api:create_app --factory --host 127.0.0.1 --port 8002`,
    url: "http://127.0.0.1:8002/api/research/capabilities",
    reuseExistingServer: false,
  },
});
