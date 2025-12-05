<template>
  <section class="route-page route-page--active legacy-host" data-testid="legacy-host">
    <header class="legacy-host__header">
      <p class="page-label">Legacy route</p>
      <p class="u-muted">This path is still served by the existing app.</p>
    </header>
    <div class="legacy-host__frame">
      <iframe
        title="Dojo legacy app"
        loading="lazy"
        :src="legacySrc"
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals allow-downloads"
      ></iframe>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

const legacyHash = computed(() => {
  const raw = route.fullPath.startsWith('/') ? route.fullPath.slice(1) : route.fullPath;
  const normalized = raw === '' ? 'transactions' : raw;
  return normalized.startsWith('/') ? normalized : `/${normalized}`;
});

const legacySrc = computed(() => `/static/index.html?embed=true#${legacyHash.value}`);
</script>

<style scoped>
.legacy-host {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.5rem;
}

.legacy-host__header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.legacy-host__frame {
  flex: 1;
  min-height: 70vh;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.legacy-host__frame iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
