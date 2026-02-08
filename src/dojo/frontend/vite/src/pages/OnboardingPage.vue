<template>
	<section class="route-page route-page--active onboarding-page" data-route="onboarding" data-testid="onboarding-page">
		<div class="wizard-shell">
			<div class="wizard-content">
				<div v-if="!isExtracting && currentStep > 1 && currentStep < totalSteps" class="wizard-progress">
					<div class="wizard-step-label">Step {{ currentStep }} of {{ totalSteps }}</div>
					<div class="progress-bar">
						<div class="progress-fill" :style="{ width: progressWidth }"></div>
					</div>
				</div>

				<div v-if="globalError" class="card form-panel__error">{{ globalError }}</div>

				<section v-if="isExtracting" class="step step-center">
					<div class="spinner"></div>
					<h3>{{ extractionStatus }}</h3>
					<p class="text-mono text-light">Validating named ranges and permissions...</p>
				</section>

				<section v-else-if="currentStep === 1" class="step step-welcome">
					<h2>Welcome</h2>
					<p class="text-light">How would you like to set up your new financial home?</p>
					<div class="tile-grid">
						<div class="tile tile-disabled">
							<h3>Start Fresh</h3>
							<p class="text-sm text-light">Create a clean slate. Best for new users or those who want a reset.</p>
						</div>
						<button type="button" class="tile tile-selected" :disabled="startPending" @click="startAspire">
							<h3>Migrate from Aspire</h3>
							<p class="text-sm text-light">
								Import your history, categories, and net worth data directly from Google Sheets.
							</p>
						</button>
					</div>
				</section>

				<section v-else-if="currentStep === 2" class="step step-center step-oauth">
					<h2>Connect Google Drive</h2>
					<p class="text-light">
						We need read-only access to your Aspire spreadsheet to analyze your history. OAuth tokens stay in memory only.
					</p>
					<div class="card oauth-card">
						<p v-if="oauthLoading" class="text-sm text-light">Checking connection...</p>
						<p v-else-if="oauth?.connected" class="tag green">Connected</p>
						<p v-else class="tag amber">Not connected</p>
						<button type="button" class="btn btn-primary" :disabled="oauthStartPending" @click="connectGoogle">
							{{ oauthStartPending ? "Opening..." : "Connect Google Account" }}
						</button>
						<p class="text-xs text-light">No tokens stored on disk.</p>
					</div>
				</section>

				<section v-else-if="currentStep === 3" class="step step-sheet">
					<h2>Which sheet are we using?</h2>
					<p class="text-light">Paste the full URL of your Aspire Budget spreadsheet.</p>
					<div class="input-group">
						<label>Spreadsheet URL</label>
						<input
							v-model="spreadsheet"
							type="text"
							class="input-underline"
							placeholder="https://docs.google.com/spreadsheets/d/..."
						/>
					</div>
					<div v-if="verifyResult" class="card verify-card" :class="verifyResult.looks_like_aspire ? 'verify-ok' : 'verify-warn'">
						<div class="font-medium">{{ verifyResult.looks_like_aspire ? "Valid Sheet Detected" : "Sheet needs attention" }}</div>
						<div class="text-sm text-light">
							Named ranges: {{ verifyResult.named_range_count }}, Missing: {{ verifyResult.missing_named_ranges.length }}
						</div>
					</div>
					<div class="step-actions">
						<button type="button" class="btn btn-secondary" :disabled="verifyPending" @click="verifySheet">
							{{ verifyPending ? "Verifying..." : "Verify (optional)" }}
						</button>
					</div>
				</section>

				<section v-else-if="currentStep === 4" class="step step-preview">
					<div class="step-heading-row">
						<div>
							<h2>We found your data</h2>
							<p class="text-light">Overview of extracted records.</p>
						</div>
						<div class="tag green">Extraction Successful</div>
					</div>
					<div class="stats-grid">
						<div class="tile text-center">
							<h3>{{ mappingAccountsCount }}</h3>
							<div class="text-xs text-mono text-light">ACCOUNTS</div>
						</div>
						<div class="tile text-center">
							<h3>{{ extractionSummary?.transactions_count || 0 }}</h3>
							<div class="text-xs text-mono text-light">TRANSACTIONS</div>
						</div>
						<div class="tile text-center">
							<h3>{{ extractionSummary?.net_worth_marks_count || 0 }}</h3>
							<div class="text-xs text-mono text-light">NW MARKS</div>
						</div>
						<div class="tile text-center">
							<h3>{{ historySpanLabel }}</h3>
							<div class="text-xs text-mono text-light">HISTORY</div>
						</div>
					</div>
				</section>

				<section v-else-if="currentStep === 5" class="step">
					<h2>Budget Accounts</h2>
					<p class="text-light">Dojo will create the following transaction-linked accounts.</p>
					<div class="card table-card">
						<table class="data-table">
							<thead>
								<tr>
									<th>Account Name</th>
									<th>Type</th>
									<th>Status</th>
									<th class="text-right">Current Balance</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="acc in mappedAccounts" :key="acc.name">
									<td class="font-medium">{{ acc.name }}</td>
									<td class="text-sm text-light">{{ acc.type }}</td>
									<td>
										<span :class="['tag', acc.status === 'Hidden' ? '' : 'green']">{{ acc.status }}</span>
									</td>
									<td class="text-right text-mono">$0.00</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section v-else-if="currentStep === 6" class="step">
					<h2>Budget Envelopes</h2>
					<p class="text-light">Mapped Aspire categories and target Dojo groups.</p>
					<div class="card table-card">
						<table class="data-table">
							<thead>
								<tr>
									<th>Category</th>
									<th>Group</th>
									<th class="text-right">Starting Balance</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="cat in mappedCategories" :key="cat.name">
									<td class="font-medium">{{ cat.name }}</td>
									<td class="text-sm text-light">{{ cat.group }}</td>
									<td class="text-right text-mono">$0.00</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section v-else-if="currentStep === 7" class="step">
					<div class="step-heading-row">
						<div>
							<h2>Transfer Exceptions</h2>
							<p class="text-light">
								We auto-paired {{ transferAutoPairs }} transfers, but {{ transferExceptions.length }} look ambiguous.
							</p>
						</div>
						<div class="tag amber" v-if="transferExceptions.length">Action Required</div>
					</div>
					<div class="card table-card">
						<table class="data-table">
							<thead>
								<tr>
									<th>Date</th>
									<th>Description</th>
									<th class="text-right">Amount</th>
									<th>Resolution</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="ex in transferExceptions" :key="ex.row_index" class="row-warning">
									<td class="text-sm text-mono text-light">{{ ex.transaction_date || "—" }}</td>
									<td class="text-sm font-medium">{{ ex.memo || ex.category_name || "Transfer" }}</td>
									<td class="text-right text-mono">{{ formatMinor(ex.amount_minor) }}</td>
									<td>
										<select class="inline-select" v-model="transferDraft[ex.row_index].kind">
											<option value="external">External Expense</option>
											<option value="opening_balance">Opening Balance</option>
											<option value="balance_adjustment">Balance Adj.</option>
										</select>
										<select
											v-if="transferDraft[ex.row_index].kind === 'external'"
											class="inline-select inline-select--sub"
											v-model="transferDraft[ex.row_index].category_id"
										>
											<option value="">Pick category...</option>
											<option v-for="opt in mappedCategories" :key="opt.aspireName" :value="opt.aspireName">
												{{ opt.name }}
											</option>
										</select>
									</td>
								</tr>
								<tr v-if="!transferExceptions.length">
									<td colspan="4" class="text-light">No transfer exceptions.</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section v-else-if="currentStep === 8" class="step">
					<h2>Consolidate Net Worth</h2>
					<p class="text-light">Mapping Aspire net worth categories to ledger accounts to prevent double-counting.</p>
					<div class="card table-card">
						<table class="data-table">
							<thead>
								<tr>
									<th>Aspire Category</th>
									<th>Dojo Account</th>
									<th>Drift Preview</th>
									<th>Strategy</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="item in duplicateRows" :key="item.name">
									<td class="font-medium">{{ item.name }}</td>
									<td class="text-sm text-light">{{ item.ledger }}</td>
									<td class="text-xs text-mono">Exact</td>
									<td><span class="tag green">Merge</span></td>
								</tr>
								<tr v-if="!duplicateRows.length">
									<td colspan="4" class="text-light">No duplicate mappings detected.</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section v-else-if="currentStep === 9" class="step">
					<h2>Migrate Net Worth</h2>
					<div class="summary-banner">
						<div class="summary-item">
							<div class="label">Total Legacy</div>
							<div class="value">{{ formatMinor(totalLegacyMinor) }}</div>
						</div>
						<div class="summary-item">
							<div class="label">Total Mapped</div>
							<div class="value">{{ formatMinor(totalMappedMinor) }}</div>
						</div>
						<div class="summary-item">
							<div class="label">Difference</div>
							<div class="value">{{ formatSignedMinor(totalMappedMinor - totalLegacyMinor) }}</div>
						</div>
					</div>

					<div v-for="row in trackForwardRows" :key="row.name" class="migration-card">
						<div class="migration-header">
							<div>
								<strong>{{ row.name }}</strong>
								<span class="text-sm text-light"> Balance: {{ formatSignedMinor(row.amount_minor) }}</span>
							</div>
							<span class="tag" :class="row.destinations.length ? 'green' : 'amber'">
								{{ row.destinations.length ? "Matched" : "Unbalanced" }}
							</span>
						</div>
						<div class="migration-body">
							<div v-for="dest in row.destinations" :key="dest.name" class="account-destination-row">
								<div>{{ dest.name }} <span class="text-xs text-light">{{ dest.account_class }}</span></div>
								<div class="text-mono">{{ formatSignedMinor(dest.starting_value_minor) }}</div>
							</div>
							<div v-if="!row.destinations.length" class="text-sm text-light">No destination accounts configured.</div>
						</div>
					</div>
				</section>

				<section v-else-if="currentStep === 10" class="step">
					<h2>Preview Migration</h2>
					<p class="text-light">Validation checks before import.</p>
					<div class="card chart-card">
						<h4 class="text-sm text-light">Net Worth History Comparison</h4>
						<svg viewBox="0 0 800 200" class="preview-chart">
							<line x1="0" y1="200" x2="800" y2="200" stroke="var(--border)" />
							<line x1="0" y1="0" x2="800" y2="0" stroke="var(--border)" />
							<path v-if="legacyPath" :d="legacyPath" fill="none" stroke="#b8b8b8" stroke-width="2" stroke-dasharray="8 4" />
							<path v-if="dojoPath" :d="dojoPath" fill="none" stroke="var(--primary)" stroke-width="2" />
						</svg>
						<div class="chart-legend text-xs text-light">
							<span>Aspire Legacy</span>
							<span>Dojo Derived</span>
						</div>
						<p v-if="previewResult && previewResult.blockers.length" class="form-panel__error">
							Blockers: {{ previewResult.blockers.join(", ") }}
						</p>
						<p v-else-if="previewResult" class="text-sm text-light">Validation ready. No blockers detected.</p>
					</div>
				</section>

				<section v-else class="step step-center">
					<div class="success-dot">✓</div>
					<h2>Migration Complete</h2>
					<p class="text-light">Your Aspire history has been successfully imported into Dojo.</p>
					<div class="card success-list">
						<h4 class="text-xs text-light">Next Steps</h4>
						<ul>
							<li>Reconcile checking account</li>
							<li>Reconcile credit card</li>
						</ul>
					</div>
				</section>
			</div>

			<div v-if="!isExtracting && currentStep > 1" class="wizard-footer">
				<div class="wizard-footer__row">
					<button v-if="currentStep > 1" type="button" class="btn btn-tertiary" @click="prevStep">Back</button>
					<div v-else></div>
					<div class="footer-actions">
						<span v-if="currentStep > 2" class="saved-pill">Saved</span>
						<button type="button" class="btn btn-primary" :disabled="nextDisabled" @click="nextStep">
							{{ primaryActionLabel }}
						</button>
					</div>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup>
import { useMutation, useQuery } from "@tanstack/vue-query";
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../services/api.js";

const router = useRouter();
const route = useRoute();

const totalSteps = 11;
const currentStep = ref(1);
const isExtracting = ref(false);
const extractionStatus = ref("Starting extraction...");
const globalError = ref("");

const spreadsheet = ref("");
const verifyResult = ref(null);
const extractionSummary = ref(null);
const mappingData = ref(null);
const transfersData = ref(null);
const decisionsData = ref(null);
const previewResult = ref(null);
const applyResult = ref(null);

const transferDraft = reactive({});

const statusQuery = useQuery({
	queryKey: ["onboarding-status"],
	queryFn: api.onboarding.status,
});

const status = computed(() => statusQuery.data.value || null);
const aspireActive = computed(
	() =>
		status.value?.onboarding_mode === "aspire" &&
		status.value?.onboarding_status === "in_progress",
);

watch(
	status,
	(value) => {
		if (
			value?.onboarding_mode === "aspire" &&
			value?.onboarding_status === "in_progress" &&
			currentStep.value < 2
		) {
			currentStep.value = 2;
		}
	},
	{ immediate: true },
);

const oauthStatusQuery = useQuery({
	queryKey: ["onboarding-google-oauth-status"],
	queryFn: api.onboarding.googleOAuthStatus,
	enabled: aspireActive,
});

const oauth = computed(() => oauthStatusQuery.data.value || null);
const oauthLoading = computed(() => oauthStatusQuery.isPending.value);

watch(
	() => route.query?.google,
	(value) => {
		if (value === "error") {
			const reason =
				typeof route.query?.reason === "string" ? route.query.reason : "";
			if (reason === "state") {
				globalError.value = "Google sign-in expired. Click Connect again.";
			} else if (reason === "invalid_client") {
				globalError.value =
					"Google OAuth client was rejected (invalid_client). Recheck the OAuth client id/secret and authorized redirect URI.";
			} else {
				globalError.value = "Google sign-in failed. Try again.";
			}
		}
		if (value === "connected") {
			oauthStatusQuery.refetch();
			if (currentStep.value < 3) {
				currentStep.value = 3;
			}
		}
	},
);

const startMutation = useMutation({
	mutationFn: api.onboarding.start,
	onSuccess: async () => {
		await statusQuery.refetch();
	},
});

const startPending = computed(() => startMutation.isPending.value);

const oauthStartMutation = useMutation({
	mutationFn: api.onboarding.googleOAuthStart,
	onSuccess: (result) => {
		window.location.assign(result.authorization_url);
	},
});

const oauthStartPending = computed(() => oauthStartMutation.isPending.value);

const verifyMutation = useMutation({
	mutationFn: (payload) => api.aspire.verifySheet(payload),
	onSuccess: (result) => {
		verifyResult.value = result;
	},
});

const verifyPending = computed(() => verifyMutation.isPending.value);

const extractMutation = useMutation({
	mutationFn: (payload) => api.aspire.extract(payload),
	onSuccess: (result) => {
		extractionSummary.value = result;
	},
});

const extractPending = computed(() => extractMutation.isPending.value);

const saveMappingMutation = useMutation({
	mutationFn: (payload) => api.aspire.saveMapping(payload),
	onSuccess: (result) => {
		mappingData.value = result;
	},
});

const saveTransfersMutation = useMutation({
	mutationFn: (payload) => api.aspire.saveTransfers(payload),
});

const saveDecisionsMutation = useMutation({
	mutationFn: (payload) => api.aspire.saveNetWorthDecisions(payload),
});

const applyMutation = useMutation({
	mutationFn: () => api.aspire.apply({ force: false }),
	onSuccess: async (result) => {
		applyResult.value = result;
		await statusQuery.refetch();
	},
});

const mappedAccounts = computed(() => {
	const accounts = mappingData.value?.mapping?.accounts || {};
	return Object.entries(accounts).map(([aspireName, value]) => ({
		aspireName,
		name: value.dojo_name,
		type: value.account_class,
		status: value.is_active ? "Active" : "Hidden",
	}));
});

const mappedCategories = computed(() => {
	const categories = mappingData.value?.mapping?.categories || {};
	return Object.entries(categories).map(([aspireName, value]) => ({
		aspireName,
		name: value.dojo_name,
		group: value.group_name,
		isActive: value.is_active,
	}));
});

const mappingAccountsCount = computed(() => mappedAccounts.value.length || 0);

const historySpanLabel = computed(() => {
	if (
		!extractionSummary.value?.transactions_date_min ||
		!extractionSummary.value?.transactions_date_max
	) {
		return "—";
	}
	const start = new Date(extractionSummary.value.transactions_date_min);
	const end = new Date(extractionSummary.value.transactions_date_max);
	const years = Math.max(
		1,
		Math.round((end - start) / (365 * 24 * 60 * 60 * 1000)),
	);
	return `${years}yr`;
});

const transferAutoPairs = computed(
	() => transfersData.value?.auto_pairs?.length || 0,
);
const transferExceptions = computed(
	() => transfersData.value?.exceptions || [],
);

watch(transferExceptions, (rows) => {
	rows.forEach((row) => {
		if (!transferDraft[row.row_index]) {
			transferDraft[row.row_index] = { kind: "external", category_id: "" };
		}
	});
});

const duplicateRows = computed(() => {
	const decisions = decisionsData.value?.decisions || {};
	return Object.entries(decisions)
		.filter(([, value]) => value.decision === "duplicate_derive_from_ledger")
		.map(([name, value]) => ({
			name,
			ledger: value.ledger_account_id || "—",
		}));
});

const trackForwardRows = computed(() => {
	const decisions = decisionsData.value?.decisions || {};
	return Object.entries(decisions)
		.filter(([, value]) => value.decision === "track_forward")
		.map(([name, value]) => ({
			name,
			amount_minor: (value.destinations || []).reduce(
				(sum, d) => sum + Number(d.starting_value_minor || 0),
				0,
			),
			destinations: value.destinations || [],
		}));
});

const totalLegacyMinor = computed(() => {
	const decisions = decisionsData.value?.decisions || {};
	return Object.values(decisions).reduce((sum, value) => {
		const destinationSum = (value.destinations || []).reduce(
			(sub, dest) => sub + Number(dest.starting_value_minor || 0),
			0,
		);
		return sum + Math.abs(destinationSum);
	}, 0);
});

const totalMappedMinor = computed(() => {
	return trackForwardRows.value.reduce((sum, row) => {
		const destinationTotal = row.destinations.reduce(
			(sub, dest) => sub + Number(dest.starting_value_minor || 0),
			0,
		);
		return sum + Math.abs(destinationTotal);
	}, 0);
});

const legacyPath = computed(() =>
	seriesPath(previewResult.value?.legacy_net_worth_bucket || []),
);
const dojoPath = computed(() =>
	seriesPath(previewResult.value?.dojo_net_worth_month_end || []),
);

const progressWidth = computed(
	() => `${((currentStep.value - 1) / (totalSteps - 1)) * 100}%`,
);

const primaryActionLabel = computed(() => {
	return currentStep.value === totalSteps ? "Finish" : "Continue";
});

const nextDisabled = computed(() => {
	if (currentStep.value === 2) {
		return oauthStartPending.value || !oauth.value?.connected;
	}
	if (currentStep.value === 3) {
		return !spreadsheet.value || extractPending.value || isExtracting.value;
	}
	if (currentStep.value === 10) {
		return applyMutation.isPending.value;
	}
	if (currentStep.value === totalSteps) {
		return false;
	}
	return false;
});

function userFacingError(error, fallback) {
	const message = String(error?.message || "").trim();
	if (!message) {
		return fallback;
	}
	if (
		message.includes("Missing optional dependencies") ||
		message.includes("uv sync --extra gsheets") ||
		message.includes("Internal Server Error") ||
		message.includes("Request failed: 5")
	) {
		return fallback;
	}
	return message;
}

const startAspire = async () => {
	globalError.value = "";
	try {
		await startMutation.mutateAsync({ onboarding_mode: "aspire" });
		currentStep.value = 2;
	} catch (error) {
		globalError.value = userFacingError(
			error,
			"Unable to start onboarding right now.",
		);
	}
};

const connectGoogle = async () => {
	globalError.value = "";
	try {
		await oauthStartMutation.mutateAsync();
	} catch (error) {
		globalError.value = userFacingError(
			error,
			"Google connection is unavailable. Check server setup and try again.",
		);
	}
};

const verifySheet = async () => {
	globalError.value = "";
	try {
		await verifyMutation.mutateAsync({ spreadsheet: spreadsheet.value });
	} catch (error) {
		globalError.value = userFacingError(
			error,
			"Unable to verify that spreadsheet.",
		);
	}
};

const startExtraction = async () => {
	globalError.value = "";
	if (!spreadsheet.value) {
		globalError.value = "Please provide a spreadsheet URL";
		return;
	}

	isExtracting.value = true;
	const stages = [
		"Connecting to Google API...",
		"Reading Spreadsheet Data...",
		"Parsing Transaction History...",
		"Analyzing Net Worth History...",
		"Done.",
	];
	let stageIndex = 0;
	const timer = setInterval(() => {
		extractionStatus.value = stages[stageIndex] || "Working...";
		stageIndex += 1;
	}, 700);

	try {
		await extractMutation.mutateAsync({ spreadsheet: spreadsheet.value });
		await loadMapping();
		isExtracting.value = false;
		currentStep.value = 4;
	} catch (error) {
		globalError.value = userFacingError(
			error,
			"Extraction failed. Confirm the sheet and connection, then try again.",
		);
		isExtracting.value = false;
	} finally {
		clearInterval(timer);
	}
};

const loadMapping = async () => {
	if (mappingData.value) {
		return;
	}
	const result = await api.aspire.getMapping();
	mappingData.value = result;
};

const saveMapping = async () => {
	if (!mappingData.value?.mapping) {
		return;
	}
	const result = await saveMappingMutation.mutateAsync({
		mapping: mappingData.value.mapping,
		complete: true,
	});
	mappingData.value = result;
};

const loadTransfers = async () => {
	const result = await api.aspire.getTransfers();
	transfersData.value = result;
};

const saveTransfers = async () => {
	const resolutions = {};
	Object.entries(transferDraft).forEach(([rowIndex, value]) => {
		resolutions[rowIndex] = {
			kind: value.kind,
			category_id: value.category_id || null,
		};
	});
	await saveTransfersMutation.mutateAsync({ resolutions });
};

const loadDecisions = async () => {
	const result = await api.aspire.getNetWorthDecisions();
	decisionsData.value = result;
};

const saveDecisions = async () => {
	if (!decisionsData.value?.decisions) {
		return;
	}
	await saveDecisionsMutation.mutateAsync({
		decisions: decisionsData.value.decisions,
		complete: true,
	});
};

const loadPreview = async () => {
	previewResult.value = await api.aspire.preview();
};

const runApply = async () => {
	applyResult.value = await applyMutation.mutateAsync();
	currentStep.value = 11;
};

const nextStep = async () => {
	globalError.value = "";
	try {
		if (currentStep.value === totalSteps) {
			goDashboard();
			return;
		}
		if (currentStep.value === 3) {
			await startExtraction();
			return;
		}
		if (currentStep.value === 4) {
			await loadMapping();
		}
		if (currentStep.value === 6) {
			await saveMapping();
			await loadTransfers();
		}
		if (currentStep.value === 7) {
			await saveTransfers();
			await loadDecisions();
		}
		if (currentStep.value === 8) {
			await saveDecisions();
		}
		if (currentStep.value === 10) {
			if (!previewResult.value) {
				await loadPreview();
			}
			await runApply();
			return;
		}
		if (currentStep.value < totalSteps) {
			currentStep.value += 1;
		}
		if (currentStep.value === 10 && !previewResult.value) {
			await loadPreview();
		}
	} catch (error) {
		globalError.value = userFacingError(error, "Unable to continue this step.");
	}
};

const prevStep = () => {
	if (currentStep.value > 1) {
		currentStep.value -= 1;
	}
};

const goDashboard = () => {
	router.push("/");
};

function formatMinor(minor) {
	const value = Number(minor || 0) / 100;
	return value.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function formatSignedMinor(minor) {
	const value = Number(minor || 0);
	const sign = value > 0 ? "+" : "";
	return `${sign}${formatMinor(value)}`;
}

function seriesPath(points) {
	if (!points || points.length < 2) {
		return "";
	}
	const values = points.map((p) => Number(p.value_minor || 0));
	const min = Math.min(...values);
	const max = Math.max(...values);
	const range = max - min || 1;
	const stepX = 800 / (points.length - 1);
	return `M ${points
		.map((point, idx) => {
			const y = 200 - ((Number(point.value_minor || 0) - min) / range) * 180;
			const x = idx * stepX;
			return `${x},${y}`;
		})
		.join(" L ")}`;
}
</script>

<style scoped>
.onboarding-page {
	max-width: 980px;
	margin: 0 auto;
}

.wizard-shell {
	display: flex;
	flex-direction: column;
	min-height: calc(100vh - 170px);
}

.wizard-step-label {
	font-family: var(--font-mono);
	font-size: 0.75rem;
	text-transform: uppercase;
	letter-spacing: 0.08em;
	color: var(--muted);
}

.progress-bar {
	height: 2px;
	margin-top: 0.75rem;
	background: var(--border);
	position: relative;
}

.progress-fill {
	position: absolute;
	left: 0;
	top: 0;
	height: 100%;
	background: var(--text);
	transition: width 0.35s ease;
}

.wizard-content {
	flex: 1;
	padding: 1rem 0 2.75rem;
}

.wizard-progress {
	margin-bottom: 1.5rem;
}

.step {
	max-width: 900px;
	margin: 0 auto;
	display: flex;
	flex-direction: column;
	gap: 1rem;
}

.step h2 {
	font-size: 1.8rem;
	font-weight: 600;
	color: var(--text);
}

.step h3 {
	font-size: 1.1rem;
	font-weight: 600;
	color: var(--text);
}

.step-center {
	align-items: center;
	justify-content: center;
	text-align: center;
	min-height: 360px;
}

.step-welcome {
	max-width: 820px;
	text-align: center;
	align-items: center;
}

.tile-grid {
	margin-top: 1.5rem;
	width: 100%;
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 1.25rem;
}

.tile {
	background: var(--surface);
	border: 1px solid var(--border);
	padding: 2rem;
	text-align: left;
	transition: all 0.2s ease;
	border-radius: 4px;
}

.tile:hover:not(:disabled) {
	transform: translateY(-2px);
	box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.tile-selected {
	border-color: var(--text);
	background: #f7f6f5;
	cursor: pointer;
}

.tile-disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

.btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	height: 44px;
	padding: 0 1rem;
	font-size: 0.95rem;
	font-weight: 500;
	border-radius: 4px;
	transition: all 0.2s ease;
}

.btn-primary {
	background: var(--text);
	color: var(--bg);
	border: 1px solid var(--text);
}

.btn-primary:hover:not(:disabled) {
	transform: translateY(-1px);
	opacity: 0.92;
}

.btn-secondary {
	background: transparent;
	color: var(--text);
	border: 1px solid var(--text);
}

.btn-tertiary {
	background: transparent;
	color: var(--muted);
	border: none;
	padding: 0;
	height: auto;
}

.btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.card {
	background: var(--surface);
	border: 1px solid var(--border);
	padding: 1.25rem;
	border-radius: 4px;
}

.oauth-card {
	max-width: 540px;
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
	align-items: center;
}

.input-group label {
	font-size: 0.85rem;
	font-weight: 500;
	color: var(--muted);
}

.input-underline {
	width: 100%;
	border: none;
	border-bottom: 2px solid var(--border);
	background: transparent;
	padding: 0.5rem 0;
	font-size: 1rem;
	color: var(--text);
}

.input-underline:focus {
	outline: none;
	border-bottom-color: var(--primary);
}

.verify-card {
	margin-top: 1rem;
}

.verify-ok {
	border-color: var(--success);
	background: #f3f8f3;
}

.verify-warn {
	border-color: #d2ad66;
	background: #fff8eb;
}

.step-actions {
	display: flex;
	gap: 0.75rem;
	justify-content: flex-end;
	margin-top: 0.75rem;
}

.step-heading-row {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
}

.stats-grid {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 1rem;
	margin-top: 1rem;
}

.text-center {
	text-align: center;
}

.text-sm {
	font-size: 0.875rem;
}

.text-xs {
	font-size: 0.75rem;
}

.text-mono {
	font-family: var(--font-mono);
}

.text-light {
	color: var(--muted);
}

.font-medium {
	font-weight: 500;
}

.tag {
	display: inline-flex;
	align-items: center;
	height: 22px;
	padding: 0 0.5rem;
	border-radius: 4px;
	font-size: 0.72rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	background: #f2f2f2;
	color: #666;
}

.tag.green {
	background: #e7f4e8;
	color: #2f6e35;
}

.tag.amber {
	background: #fff5de;
	color: #8a6406;
}

.table-card {
	padding: 0;
	overflow: hidden;
}

.data-table {
	width: 100%;
	border-collapse: collapse;
}

.data-table th {
	text-align: left;
	font-size: 0.72rem;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--muted);
	padding: 0.6rem 0.75rem;
	border-bottom: 1px solid var(--border);
	background: #fafafa;
}

.data-table td {
	padding: 0.8rem 0.75rem;
	border-bottom: 1px solid var(--border);
	font-size: 0.93rem;
}

.text-right {
	text-align: right;
}

.row-warning {
	background: #fff8e9;
}

.inline-select {
	width: 100%;
	padding: 0.3rem;
	border: none;
	border-bottom: 1px solid var(--border);
	background: transparent;
	font-size: 0.85rem;
}

.inline-select--sub {
	margin-top: 0.35rem;
}

.summary-banner {
	background: var(--text);
	color: #fff;
	padding: 1rem;
	border-radius: 4px;
	display: flex;
	justify-content: space-around;
	margin-bottom: 1rem;
}

.summary-item {
	text-align: center;
}

.summary-item .label {
	font-size: 0.68rem;
	text-transform: uppercase;
	letter-spacing: 0.07em;
	opacity: 0.75;
}

.summary-item .value {
	font-family: var(--font-mono);
	font-size: 1rem;
	font-weight: 700;
	margin-top: 0.2rem;
}

.migration-card {
	border: 1px solid var(--border);
	border-radius: 4px;
	background: var(--surface);
	overflow: hidden;
	margin-bottom: 0.9rem;
}

.migration-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 0.75rem 1rem;
	background: #fafafa;
	border-bottom: 1px solid var(--border);
	gap: 1rem;
}

.migration-body {
	padding: 1rem;
}

.account-destination-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 0.6rem;
	border: 1px solid var(--border);
	border-radius: 4px;
	margin-bottom: 0.5rem;
	background: #fcfcfb;
}

.chart-card {
	padding: 1rem;
}

.preview-chart {
	width: 100%;
	height: 180px;
	margin-top: 0.75rem;
}

.chart-legend {
	display: flex;
	gap: 1rem;
	justify-content: center;
	margin-top: 0.5rem;
}

.success-dot {
	width: 72px;
	height: 72px;
	border-radius: 999px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	background: var(--text);
	color: #fff;
	font-size: 2rem;
	font-weight: 700;
}

.success-list {
	width: 100%;
	max-width: 420px;
	text-align: left;
}

.success-list ul {
	margin-top: 0.5rem;
	padding-left: 1rem;
	display: grid;
	gap: 0.4rem;
}

.wizard-footer {
	padding: 1rem 0;
	border-top: 1px solid var(--border);
	background: var(--bg);
	position: sticky;
	bottom: 0;
}

.wizard-footer__row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 1rem;
}

.footer-actions {
	display: flex;
	align-items: center;
	gap: 0.75rem;
}

.saved-pill {
	font-size: 0.75rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--primary);
}

.spinner {
	width: 40px;
	height: 40px;
	border: 3px solid var(--border);
	border-top-color: var(--text);
	border-radius: 50%;
	animation: spin 0.8s linear infinite;
	margin-bottom: 1rem;
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}

@media (max-width: 960px) {
	.onboarding-page {
		max-width: 100%;
	}

	.tile-grid,
	.stats-grid {
		grid-template-columns: 1fr;
	}

	.step-heading-row,
	.wizard-footer__row {
		flex-direction: column;
		align-items: flex-start;
	}

	.summary-banner {
		flex-direction: column;
		gap: 0.6rem;
	}
}
</style>
