import { describe, expect, it } from "vitest";
import LegacyHost from "./components/LegacyHost.vue";
import TransactionsPage from "./pages/TransactionsPage.vue";
import router from "./router";

describe("router configuration", () => {
	const routes = router.getRoutes();

	it("redirects the root path to transactions", () => {
		const rootRoute = routes.find((route) => route.path === "/");
		expect(rootRoute?.redirect).toBe("/transactions");
	});

	it("includes migrated and legacy catch-all routes", () => {
		const txRoute = routes.find((route) => route.path === "/transactions");
		expect(txRoute?.components?.default).toBe(TransactionsPage);

		const catchAll = routes.find((route) => route.path === "/:pathMatch(.*)*");
		expect(catchAll?.components?.default).toBe(LegacyHost);
	});

	it("uses the expected active link class", () => {
		expect(router.options.linkExactActiveClass).toBe(
			"app-header__link--active",
		);
	});
});
