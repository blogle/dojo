<template>
  <div
    v-if="open"
    class="modal-overlay is-visible"
    style="display: flex;"
    @click.self="handleCancel"
  >
    <div
      class="modal confirm-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      data-testid="confirm-dialog"
    >
      <header class="modal__header">
        <div>
          <p class="stat-card__label">{{ label }}</p>
          <h2 :id="titleId">{{ title }}</h2>
        </div>
        <button
          class="modal__close"
          type="button"
          data-testid="confirm-dialog-close"
          :disabled="pending"
          @click="handleCancel"
        >
          ×
        </button>
      </header>

      <div class="modal__body">
        <p data-testid="confirm-dialog-message">{{ message }}</p>
        <p
          v-if="details"
          class="u-muted u-small-note"
          data-testid="confirm-dialog-details"
        >
          {{ details }}
        </p>

        <div class="form-panel__actions form-panel__actions--split">
          <button
            type="button"
            class="button button--secondary"
            data-testid="confirm-dialog-cancel"
            :disabled="pending"
            @click="handleCancel"
          >
            {{ cancelLabel }}
          </button>
          <button
            type="button"
            class="button button--primary"
            data-testid="confirm-dialog-confirm"
            :disabled="pending"
            @click="handleConfirm"
          >
            {{ pending ? pendingLabel : confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	label: { type: String, default: "Confirm" },
	title: { type: String, default: "Are you sure?" },
	message: { type: String, default: "" },
	details: { type: String, default: "" },
	confirmLabel: { type: String, default: "Confirm" },
	cancelLabel: { type: String, default: "Cancel" },
	pending: { type: Boolean, default: false },
	pendingLabel: { type: String, default: "Working…" },
	dialogId: { type: String, default: "" },
});

const emit = defineEmits(["confirm", "cancel"]);

const titleId = computed(() =>
	props.dialogId ? `${props.dialogId}-title` : "confirm-dialog-title",
);

const handleCancel = () => emit("cancel");
const handleConfirm = () => emit("confirm");
</script>
