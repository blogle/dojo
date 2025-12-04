import { createRouter, createWebHashHistory } from 'vue-router';
import TransactionsPage from './pages/TransactionsPage.vue';
import LegacyHost from './components/LegacyHost.vue';

const routes = [
  {
    path: '/',
    redirect: '/transactions',
  },
  {
    path: '/transactions',
    component: TransactionsPage,
  },
  {
    path: '/:pathMatch(.*)*',
    component: LegacyHost,
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  linkExactActiveClass: 'app-header__link--active',
});

export default router;
