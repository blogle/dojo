import { createRouter, createWebHashHistory } from "vue-router";
import AccountDetailPage from "./pages/AccountDetailPage.vue";
import AccountsPage from "./pages/AccountsPage.vue";
import BudgetPage from "./pages/BudgetPage.vue";
import DashboardPage from "./pages/DashboardPage.vue";
import OnboardingPage from "./pages/OnboardingPage.vue";
import TransactionsPage from "./pages/TransactionsPage.vue";
import TransfersPage from "./pages/TransfersPage.vue";

const routes = [
	{
		path: "/",
		component: DashboardPage,
	},
	{
		path: "/dashboard",
		redirect: "/",
	},
	{
		path: "/transactions",
		component: TransactionsPage,
	},
	{
		path: "/accounts",
		component: AccountsPage,
	},
	{
		path: "/accounts/:accountId",
		component: AccountDetailPage,
	},
	{
		path: "/accounts/:accountId/reconcile",
		component: AccountDetailPage,
	},
	{
		path: "/accounts/:accountId/verify-holdings",
		component: AccountDetailPage,
	},
	{
		path: "/accounts/:accountId/valuation",
		component: AccountDetailPage,
	},
	{
		path: "/budgets",
		component: BudgetPage,
	},
	{
		path: "/onboarding",
		component: OnboardingPage,
	},
	{
		path: "/transfers",
		component: TransfersPage,
	},
	{
		path: "/investments/:accountId",
		redirect: (to) => ({
			path: `/accounts/${to.params.accountId}`,
			query: to.query,
		}),
	},
	{
		path: "/:pathMatch(.*)*",
		redirect: "/",
	},
];

const router = createRouter({
	history: createWebHashHistory(),
	routes,
	linkExactActiveClass: "app-header__link--active",
});

let onboardingCache = null;
let onboardingCacheAt = 0;

const loadOnboardingStatus = async () => {
	const now = Date.now();
	if (onboardingCache && now - onboardingCacheAt < 5000) {
		return onboardingCache;
	}

	const response = await fetch("/api/onboarding/status");
	if (!response.ok) {
		throw new Error(`onboarding status request failed: ${response.status}`);
	}

	onboardingCache = await response.json();
	onboardingCacheAt = now;
	return onboardingCache;
};

router.beforeEach(async (to) => {
	try {
		const status = await loadOnboardingStatus();
		if (status?.should_onboard && to.path !== "/onboarding") {
			return "/onboarding";
		}
		if (!status?.should_onboard && to.path === "/onboarding") {
			return "/";
		}
	} catch {
		return true;
	}

	return true;
});

export default router;
