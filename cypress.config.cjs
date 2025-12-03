const { spawn } = require("node:child_process");
const path = require("node:path");
const http = require("node:http");

const defineConfig = (config) => config;
const log = (...args) => console.info("[cypress-config]", ...args);

const SERVER_URL = "http://127.0.0.1:8765";
const SERVER_PROBE_URL = `${SERVER_URL}/api/net-worth/current`;
const E2E_DB_PATH = path.join(__dirname, "data", "e2e-ledger.duckdb");

let serverProcess = null;
let serverPromise = null;

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const probeServer = () =>
	new Promise((resolve) => {
		const req = http.get(SERVER_PROBE_URL, (res) => {
			res.resume();
			const ok =
				res.statusCode && res.statusCode >= 200 && res.statusCode < 500;
			resolve(ok);
		});
		req.on("error", () => resolve(false));
	});

const waitForServer = async (timeoutMs = 30000, intervalMs = 250) => {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		if (await probeServer()) {
			return;
		}
		await delay(intervalMs);
	}
	throw new Error(`Server failed to start within ${timeoutMs} ms`);
};

const stopServer = async () => {
	if (!serverProcess) {
		return;
	}

	const proc = serverProcess;
	serverProcess = null;

	return new Promise((resolve) => {
		const timeout = setTimeout(() => {
			if (!proc.killed) {
				proc.kill("SIGKILL");
			}
		}, 5000);

		proc.once("exit", () => {
			clearTimeout(timeout);
			serverPromise = null;
			resolve();
		});

		proc.kill("SIGTERM");
	});
};

const startServer = async () => {
	if (serverProcess) {
		return;
	}

	const command = `DOJO_DB_PATH="${E2E_DB_PATH}" DOJO_TESTING="1" uv run python -m tests.e2e.prepare_db && DOJO_DB_PATH="${E2E_DB_PATH}" DOJO_TESTING="1" uv run uvicorn dojo.core.app:create_app --factory --host 127.0.0.1 --port 8765`;

	serverProcess = spawn("bash", ["-lc", command], {
		env: {
			...process.env,
			DOJO_DB_PATH: E2E_DB_PATH,
			DOJO_TESTING: "1",
		},
		stdio: "inherit",
	});

	serverProcess.on("exit", (code, signal) => {
		if (code !== null) {
			console.info(`[cypress] test server exited with code ${code}`);
		} else if (signal) {
			console.info(`[cypress] test server terminated via ${signal}`);
		}
		serverProcess = null;
		serverPromise = null;
	});

	serverProcess.on("error", (error) => {
		console.error("[cypress] failed to start test server:", error);
	});

	try {
		await waitForServer();
	} catch (error) {
		await stopServer();
		throw error;
	}
};

const ensureServer = () => {
	if (!serverPromise) {
		serverPromise = startServer()
			.then(() => {
				log("test server ready at", SERVER_URL);
			})
			.catch((error) => {
				serverPromise = null;
				throw error;
			});
	}
	return serverPromise;
};

const registerShutdownHook = () => {
	process.on("exit", () => {
		if (serverProcess) {
			serverProcess.kill("SIGTERM");
		}
	});

	["SIGINT", "SIGTERM"].forEach((signal) => {
		process.on(signal, async () => {
			await stopServer();
			process.exit(0);
		});
	});
};

registerShutdownHook();
ensureServer().catch((error) => {
	console.error("[cypress-config] failed to start test server:", error);
	process.exitCode = 1;
});

module.exports = defineConfig({
	e2e: {
		baseUrl: SERVER_URL,
		specPattern: "cypress/e2e/**/*.cy.js",
		supportFile: "cypress/support/e2e.js",
		video: false,
		defaultCommandTimeout: 10000,
		setupNodeEvents(on, config) {
			on("before:run", async () => {
				await ensureServer();
			});
			on("before:spec", async () => {
				await ensureServer();
			});
			on("before:browser:launch", (browser, launchOptions) => {
				if (browser.family === "chromium") {
					// The Electron/Chromium sandbox cannot initialize inside the CI sandbox,
					// so disable it to prevent SIGTRAP crashes.
					launchOptions.args = launchOptions.args || [];
					launchOptions.args.push(
						"--no-sandbox",
						"--disable-dev-shm-usage",
						"--disable-setuid-sandbox",
						"--disable-gpu",
					);
				}
				return launchOptions;
			});
			on("after:run", async () => {
				await stopServer();
			});
			return config;
		},
	},
});
