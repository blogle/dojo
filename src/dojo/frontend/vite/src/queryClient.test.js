import { QueryClient } from "@tanstack/vue-query";
import { describe, expect, it } from "vitest";
import queryClient from "./queryClient";

describe("queryClient bridge", () => {
	it("exports a QueryClient instance", () => {
		expect(queryClient).toBeInstanceOf(QueryClient);
	});

	it("attaches the client to window for legacy invalidation hooks", () => {
		expect(globalThis.window?.dojoQueryClient).toBe(queryClient);
	});
});
