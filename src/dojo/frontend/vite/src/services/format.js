const currencyFormatter = new Intl.NumberFormat("en-US", {
	style: "currency",
	currency: "USD",
	minimumFractionDigits: 2,
});

export const formatAmount = (minor = 0) =>
	currencyFormatter.format((minor || 0) / 100);

export const minorToDollars = (minor = 0) =>
	(Number(minor || 0) / 100).toFixed(2);

export const dollarsToMinor = (value) => {
	const parsed = Number.parseFloat(value);
	if (Number.isNaN(parsed)) {
		return 0;
	}
	return Math.round(parsed * 100);
};

export const todayISO = () => {
	const today = new Date();
	return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
};

export const currentMonthStartISO = () => {
	const today = new Date();
	return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-01`;
};
