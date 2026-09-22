import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8000",
    viewport: { width: 1440, height: 1050 },
  },
  webServer: {
    command:
      "cd .. && REDLINE_DB=/tmp/redline-browser-tests.sqlite3 .venv/bin/python demo.py",
    url: "http://127.0.0.1:8000/api/snapshot",
    reuseExistingServer: !process.env.CI,
  },
});
