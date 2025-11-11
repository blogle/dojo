import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const e2eDbPath = path.join(__dirname, "data", "e2e-ledger.duckdb");
const serverCommand = `DOJO_DB_PATH="${e2eDbPath}" uv run python -m tests.e2e.prepare_db && DOJO_DB_PATH="${e2eDbPath}" uv run uvicorn dojo.core.app:app --host 127.0.0.1 --port 8765`;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: "http://127.0.0.1:8765",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: `bash -lc '${serverCommand.replace(/'/g, `'\\''`)}'`,
    url: "http://127.0.0.1:8765",
    reuseExistingServer: !process.env.CI,
    env: {
      DOJO_DB_PATH: e2eDbPath,
    },
  },
});
