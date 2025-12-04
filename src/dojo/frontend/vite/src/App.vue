<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink to="/" class="app-header__logo">DOJO</RouterLink>
      <nav class="app-header__nav" aria-label="Primary">
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
          to="/allocations"
          class="app-header__link"
          data-route-link="allocations"
        >
          Allocations
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
import { RouterLink, RouterView } from 'vue-router';
</script>
