const waiters = new Set();
let pendingAllocations = 0;

export const notifyAllocationStart = () => {
	pendingAllocations += 1;
};

export const notifyAllocationEnd = () => {
	if (pendingAllocations <= 0) {
		return;
	}
	pendingAllocations -= 1;
	if (pendingAllocations === 0) {
		waiters.forEach((resolve) => {
			resolve();
		});
		waiters.clear();
	}
};

export const waitForPendingAllocations = () => {
	if (pendingAllocations === 0) {
		return Promise.resolve();
	}
	return new Promise((resolve) => {
		waiters.add(resolve);
	});
};
