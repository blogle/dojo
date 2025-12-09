import { createRouter, createWebHashHistory } from "vue-router";
import LegacyHost from "./components/LegacyHost.vue";
import AccountsPage from "./pages/AccountsPage.vue";
import AllocationsPage from "./pages/AllocationsPage.vue";
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
		path: "/budgets",
		component: BudgetPage,
	},
	{
		path: "/allocations",
		component: AllocationsPage,
	},
	{
		path: "/transfers",
		component: TransfersPage,
	},
	{
		path: "/:pathMatch(.*)*",
		component: LegacyHost,
	},
];

const router = createRouter({
	history: createWebHashHistory(),
	routes,
	linkExactActiveClass: "app-header__link--active",
});

export default router;
