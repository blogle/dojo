import { createRouter, createWebHashHistory } from "vue-router";
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
		path: "/budgets",
		component: BudgetPage,
	},
	{
		path: "/transfers",
		component: TransfersPage,
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
