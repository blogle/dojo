<template>
  <section class="route-page route-page--active account-detail-page" data-route="account-detail">
    <header class="investments-header">
      <div>
        <p class="page-label">
          <router-link to="/accounts">Accounts</router-link>
          <span v-if="accountId"> &gt; {{ account?.name || accountId }}</span>
        </p>
      </div>
    </header>

    <p v-if="accountLoading" class="u-muted">Loading account…</p>
    <pre v-else class="u-mono">{{ account }}</pre>
  </section>
</template>

<script setup>
import { useQuery } from "@tanstack/vue-query";
import { computed } from "vue";
import { useRoute } from "vue-router";
import { api } from "../services/api.js";

const route = useRoute();
const accountId = computed(() => route.params.accountId);

const accountQuery = useQuery({
	queryKey: computed(() => ["accounts", accountId.value]),
	queryFn: () => api.accounts.get(accountId.value),
	enabled: computed(() => Boolean(accountId.value)),
});

const account = computed(() => accountQuery.data.value);
const accountLoading = computed(
	() => accountQuery.isPending.value || accountQuery.isFetching.value,
);
</script>
