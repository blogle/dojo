<template>
  <div class="app-shell">
    <header class="app-header" :class="{ 'app-header--onboarding': isOnboardingRoute }">
      <RouterLink to="/" class="app-header__logo">DOJO</RouterLink>
      <p v-if="isOnboardingRoute" class="app-header__context">Onboarding</p>
      <nav v-else class="app-header__nav" aria-label="Primary">
        <RouterLink to="/" class="app-header__link" data-route-link="dashboard">
          Dashboard
        </RouterLink>
        <RouterLink
          to="/transactions"
          class="app-header__link"
          data-route-link="transactions"
        >
          Transactions
        </RouterLink>
        <RouterLink
          to="/transfers"
          class="app-header__link"
          data-route-link="transfers"
        >
          Transfers
        </RouterLink>
        <RouterLink
          to="/accounts"
          class="app-header__link"
          data-route-link="accounts"
        >
          Assets &amp; Liabilities
        </RouterLink>
        <RouterLink to="/budgets" class="app-header__link" data-route-link="budgets">
          Budgets
        </RouterLink>
        <noscript><span class="u-muted">Enable JavaScript for navigation.</span></noscript>
      </nav>
    </header>

    <main class="app-shell__content" id="page-container">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { useRoute } from "vue-router";

const route = useRoute();
const isOnboardingRoute = computed(() => route.path === "/onboarding");
</script>
