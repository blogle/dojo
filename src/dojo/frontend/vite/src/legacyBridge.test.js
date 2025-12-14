import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./services/api.js";
import queryClient from "./queryClient.js";

// Mock the queryClient module
vi.mock("./queryClient.js", () => ({
	default: {
		invalidateQueries: vi.fn(),
	},
}));

const mockResponse = (payload = {}) => ({
	ok: true,
	status: 200,
	text: vi.fn().mockResolvedValue(JSON.stringify(payload)),
});

const LEDGER_KEYS = [
	"transactions",
	"reconciliation-worksheet",
	"budget-allocations",
	"ready-to-assign",
	"accounts",
	"budget-categories",
];

describe("legacy mutation invalidations", () => {
	let originalFetch;

	beforeEach(() => {
		originalFetch = globalThis.fetch;
		vi.clearAllMocks();
	});

	afterEach(() => {
		globalThis.fetch = originalFetch;
		vi.restoreAllMocks();
	});

	it("invalidates shared queries after creating a transaction", async () => {
		globalThis.fetch = vi.fn().mockResolvedValue(mockResponse({ ok: true }));

		await api.transactions.create({ memo: "test" });

		expect(queryClient.invalidateQueries).toHaveBeenCalledTimes(
			LEDGER_KEYS.length,
		);
		const calledKeys = queryClient.invalidateQueries.mock.calls.map(
			([args]) => args?.queryKey?.[0],
		);
		expect(calledKeys).toEqual(LEDGER_KEYS);
	});

	it("uses the update endpoint and invalidates queries after editing a transaction", async () => {
		const fetchMock = vi.fn().mockResolvedValue(mockResponse({ ok: true }));
		globalThis.fetch = fetchMock;

		await api.transactions.update("tx-123", { memo: "updated" });

		expect(fetchMock).toHaveBeenCalledWith(
			"/api/transactions/tx-123",
			expect.objectContaining({ method: "PUT" }),
		);
		expect(queryClient.invalidateQueries).toHaveBeenCalledTimes(
			LEDGER_KEYS.length,
		);
	});
});
