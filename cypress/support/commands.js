// cypress/support/commands.js

const DEFAULT_TEST_DATE = "2025-12-15";

const testDate = () => Cypress.env("TEST_DATE") || DEFAULT_TEST_DATE;

const withTestDateHeader = (options) => {
	const headers = { ...(options.headers || {}) };
	if (!headers["x-test-date"] && !headers["X-Test-Date"]) {
		headers["x-test-date"] = testDate();
	}
	return { ...options, headers };
};

Cypress.Commands.overwrite("request", (originalFn, ...args) => {
	if (args.length === 0) {
		return originalFn();
	}

	if (typeof args[0] === "object" && args[0] !== null) {
		return originalFn(withTestDateHeader(args[0]));
	}

	if (typeof args[0] === "string" && typeof args[1] === "string") {
		const [method, url, body] = args;
		return originalFn(withTestDateHeader({ method, url, body }));
	}

	if (
		typeof args[0] === "string" &&
		args.length === 2 &&
		typeof args[1] === "object" &&
		args[1] !== null
	) {
		const [url, body] = args;
		return originalFn(withTestDateHeader({ url, body }));
	}

	if (typeof args[0] === "string") {
		const [url] = args;
		return originalFn(withTestDateHeader({ url }));
	}

	return originalFn(...args);
});

Cypress.Commands.add("resetDatabase", () => {
	cy.request("POST", "/api/testing/reset_db");
});

Cypress.Commands.add("seedDatabase", (fixturePath) => {
	cy.request("POST", "/api/testing/seed_db", { fixture: fixturePath });
});

// Helper to ensure backend data is ready before UI interaction
// Retry fetching the URL until the predicate returns true
Cypress.Commands.add("ensureBackendState", (url, predicate, options = {}) => {
	const { timeout = 10000, interval = 500 } = options;
	const startTime = Date.now();

	const check = () => {
		cy.request({ url, failOnStatusCode: false }).then((res) => {
			if (Date.now() - startTime > timeout) {
				throw new Error(`ensureBackendState timed out for ${url}`);
			}
			if (res.status === 200 && predicate(res.body)) {
				return;
			}
			cy.wait(interval);
			check();
		});
	};
	check();
});

// Custom command for selecting elements by data-testid
Cypress.Commands.add("getBySel", (selector, ...args) => {
	return cy.get(`[data-testid=${selector}]`, ...args);
});
