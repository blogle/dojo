import { reactive } from "vue";

let nextToastId = 1;

const toastStore = reactive({
	toasts: [],
});

export const useToastStore = () => toastStore;

export const removeToast = (toastId) => {
	const index = toastStore.toasts.findIndex((toast) => toast.id === toastId);
	if (index === -1) {
		return;
	}
	const [toast] = toastStore.toasts.splice(index, 1);
	if (toast?.timeoutId) {
		clearTimeout(toast.timeoutId);
	}
};

export const pushToast = ({
	message,
	kind = "info",
	actionLabel = "",
	onAction = null,
	timeoutMs = 6000,
}) => {
	const toastId = nextToastId++;
	const toast = {
		id: toastId,
		message: message || "",
		kind,
		actionLabel,
		onAction,
		isRunning: false,
		timeoutId: null,
	};

	if (timeoutMs > 0) {
		toast.timeoutId = setTimeout(() => removeToast(toastId), timeoutMs);
	}

	toastStore.toasts.push(toast);
	return toastId;
};

export const runToastAction = async (toast) => {
	if (!toast?.onAction || toast.isRunning) {
		return;
	}

	toast.isRunning = true;
	try {
		await toast.onAction();
		removeToast(toast.id);
	} catch (error) {
		toast.isRunning = false;
		pushToast({
			kind: "error",
			message: error?.message || "Action failed.",
		});
	}
};
