<template>
  <table :class="tableClass">
    <slot />
  </table>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	variant: {
		type: String,
		default: "",
	},
});

const tableClass = computed(() => {
	const classes = ["ledger-table"];
	if (props.variant) {
		classes.push(`ledger-table--${props.variant}`);
	}
	return classes;
});
</script>
