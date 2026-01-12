import { describe, expect, it } from "vitest";
import DashboardPage from "./pages/DashboardPage.vue";
import TransactionsPage from "./pages/TransactionsPage.vue";
import router from "./router";

describe("router configuration", () => {
	const routes = router.getRoutes();

	it("uses the dashboard as the root route", () => {
		const rootRoute = routes.find((route) => route.path === "/");
		expect(rootRoute?.components?.default).toBe(DashboardPage);
	});

	it("includes migrated routes and catch-all redirect", () => {
		const txRoute = routes.find((route) => route.path === "/transactions");
		expect(txRoute?.components?.default).toBe(TransactionsPage);

		const dashboardRedirect = routes.find(
			(route) => route.path === "/dashboard",
		);
		expect(dashboardRedirect?.redirect).toBe("/");

		const catchAll = routes.find((route) => route.path === "/:pathMatch(.*)*");
		expect(catchAll?.redirect).toBe("/");
	});

	it("uses the expected active link class", () => {
		expect(router.options.linkExactActiveClass).toBe(
			"app-header__link--active",
		);
	});
});
