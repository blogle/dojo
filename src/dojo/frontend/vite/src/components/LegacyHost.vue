<template>
  <section class="route-page route-page--active app-bridge" data-testid="app-bridge">
    <div class="app-bridge__frame">
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
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const legacyHash = computed(() => {
	const raw = route.fullPath.startsWith("/")
		? route.fullPath.slice(1)
		: route.fullPath;
	const normalized = raw === "" ? "transactions" : raw;
	return normalized.startsWith("/") ? normalized : `/${normalized}`;
});

const legacySrc = computed(
	() => `/static/index.html?embed=true#${legacyHash.value}`,
);
</script>

<style scoped>
.app-bridge {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0; /* Reduced padding as there is no header now, or keep it if layout needs it */
  height: 100%; /* Ensure it takes full height */
}

.app-bridge__frame {
  flex: 1;
  min-height: 70vh;
  border: none; /* Remove border if we want it seamless */
  overflow: hidden;
  background: #fff;
}

.app-bridge__frame iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
