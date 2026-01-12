<template>
  <div class="reconciliation-adapter reconciliation-adapter--stub">
    <div class="reconciliation-adapter__placeholder">
      <p class="reconciliation-adapter__placeholder-title">Investment positions reconciliation</p>
      <p class="reconciliation-adapter__placeholder-text">
        This adapter will support reconciling ticker, quantity, cost basis, and cash balance
        against your brokerage statement.
      </p>
      <div class="reconciliation-adapter__placeholder-status">
        <span class="u-muted">Status:</span>
        <span class="reconciliation-adapter__status-badge reconciliation-adapter__status-badge--stub">Stub</span>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
	account: { type: Object, default: null },
	accounts: { type: Array, default: () => [] },
	categories: { type: Array, default: () => [] },
});

const emit = defineEmits(["ready", "close", "commit"]);

emit("ready", {
	commitLabel: null,
	commitDisabled: true,
});
</script>

<style scoped>
.reconciliation-adapter--stub {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.reconciliation-adapter__placeholder {
  max-width: 500px;
  text-align: center;
  padding: 2rem;
  border: 1px dashed var(--border);
  border-radius: 8px;
}

.reconciliation-adapter__placeholder-title {
  font-family: var(--font-sans);
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 0.75rem 0;
  color: var(--text);
}

.reconciliation-adapter__placeholder-text {
  font-family: var(--font-sans);
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0 0 1.5rem 0;
  color: var(--muted);
}

.reconciliation-adapter__placeholder-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.reconciliation-adapter__status-badge {
  padding: 0.25rem 0.6rem;
  border-radius: 12px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.reconciliation-adapter__status-badge--stub {
  background-color: var(--muted-bg);
  color: var(--muted);
}
</style>
