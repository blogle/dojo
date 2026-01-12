<template>
  <div
    id="toast-stack"
    class="toast-stack"
    data-testid="toast-stack"
    aria-live="polite"
    aria-relevant="additions removals"
  >
    <div
      v-for="toast in toasts"
      :key="toast.id"
      class="toast"
      role="status"
      :data-kind="toast.kind"
      data-testid="toast"
    >
      <div class="toast__message">{{ toast.message }}</div>
      <div class="toast__actions">
        <button
          v-if="toast.actionLabel"
          type="button"
          class="button button--tertiary toast__button"
          data-testid="toast-action"
          :disabled="toast.isRunning"
          @click="() => handleAction(toast)"
        >
          {{ toast.isRunning ? "Working…" : toast.actionLabel }}
        </button>
        <button
          type="button"
          class="button button--tertiary toast__button"
          data-testid="toast-dismiss"
          aria-label="Dismiss"
          @click="() => dismiss(toast.id)"
        >
          ×
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import {
	removeToast,
	runToastAction,
	useToastStore,
} from "../services/toasts.js";

const store = useToastStore();

const toasts = computed(() => store.toasts);

const dismiss = (toastId) => {
	removeToast(toastId);
};

const handleAction = async (toast) => {
	await runToastAction(toast);
};
</script>

<style scoped>
.toast {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.toast__message {
  white-space: pre-wrap;
}

.toast__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.toast__button {
  padding: 0.15rem 0.35rem;
  font-size: 0.85rem;
}
</style>
