import { createRouter, createWebHashHistory } from "vue-router";
import AccountDetailPage from "./pages/AccountDetailPage.vue";
import AccountsPage from "./pages/AccountsPage.vue";
import BudgetPage from "./pages/BudgetPage.vue";
import TransactionsPage from "./pages/TransactionsPage.vue";
import TransfersPage from "./pages/TransfersPage.vue";

const routes = [
	{
		path: "/",
		redirect: "/transactions",
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
		redirect: "/transactions",
	},
];

const router = createRouter({
	history: createWebHashHistory(),
	routes,
	linkExactActiveClass: "app-header__link--active",
});

export default router;
