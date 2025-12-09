import { describe, expect, it } from "vitest";
import TransactionsPage from "./pages/TransactionsPage.vue";
import router from "./router";

describe("router configuration", () => {
	const routes = router.getRoutes();

	it("redirects the root path to transactions", () => {
		const rootRoute = routes.find((route) => route.path === "/");
		expect(rootRoute?.redirect).toBe("/transactions");
	});

	it("includes migrated routes and catch-all redirect", () => {
		const txRoute = routes.find((route) => route.path === "/transactions");
		expect(txRoute?.components?.default).toBe(TransactionsPage);

		const catchAll = routes.find((route) => route.path === "/:pathMatch(.*)*");
		expect(catchAll?.redirect).toBe("/transactions");
	});

	it("uses the expected active link class", () => {
		expect(router.options.linkExactActiveClass).toBe(
			"app-header__link--active",
		);
	});
});