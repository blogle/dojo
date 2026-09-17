<template>
	<section class="route-page route-page--active onboarding-page" data-route="onboarding" data-testid="onboarding-page">
		<div class="wizard-shell">
			<div class="wizard-header">
				<div class="wizard-header__row">
					<div class="wizard-brand">
						<div class="wizard-logo">DOJO</div>
						<div class="wizard-context">Onboarding</div>
					</div>
					<div v-if="!isExtracting && currentStep > 1 && currentStep < totalSteps" class="wizard-progress__header">
						<div class="wizard-step-meta">{{ stepTitleLabel }} · Step {{ currentStep }} of {{ totalSteps }}</div>
						<div :class="['validation-badge', validationBadgeClass]" :title="validationBadgeHint">
							{{ validationBadgeLabel }} <span class="validation-badge__info">i</span>
						</div>
					</div>
				</div>
				<div v-if="!isExtracting && currentStep > 1 && currentStep < totalSteps" class="progress-bar">
					<div class="progress-fill" :style="{ width: progressWidth }"></div>
				</div>
			</div>

			<div class="wizard-content">
				<div v-if="globalError" class="card form-panel__error">{{ globalError }}</div>

				<section v-if="isExtracting" class="step step-center">
					<div class="spinner"></div>
					<h3>{{ extractionStatus }}</h3>
					<p class="text-mono text-light">Validating named ranges and permissions...</p>
				</section>

				<section v-else-if="currentStep === 1" class="step step-welcome">
					<h2>Welcome to Dojo</h2>
					<p class="text-light">How would you like to set up your new financial home?</p>
					<div class="tile-grid">
						<div class="tile tile-disabled">
							<div class="tile-icon">◌</div>
							<h3>Start Fresh</h3>
							<p class="text-sm text-light">Skip migration and start with an empty workspace.</p>
						</div>
						<button type="button" class="tile tile-selected" :disabled="startPending" @click="startAspire">
							<div class="tile-icon tile-icon--accent">↔</div>
							<h3>Migrate from Aspire</h3>
							<p class="text-sm text-light">Import your history, categories, and net worth data.</p>
						</button>
					</div>
				</section>

				<section v-else-if="currentStep === 2" class="step step-center step-oauth">
					<h2>Connect Google Drive</h2>
					<p class="text-light">
						We request read-only access to locate your Aspire sheet and extract named ranges only. OAuth tokens stay in memory and are never written to disk.
					</p>
					<div class="card oauth-card">
						<p v-if="oauthLoading" class="text-sm text-light">Checking connection...</p>
						<button type="button" class="btn btn-primary" :disabled="oauthStartPending" @click="connectGoogle">
							<span class="btn-glyph">G</span>{{ oauthStartPending ? "Opening..." : "Connect Google Account" }}
						</button>
					</div>
				</section>

				<section v-else-if="currentStep === 3" class="step step-sheet">
					<h2>Which sheet are we using?</h2>
					<p class="text-light">Paste the Google Sheets URL for your Aspire workbook.</p>
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
					<p class="text-light">Confirm transaction-linked accounts and their balances.</p>
					<div class="card table-card">
						<table class="data-table">
							<thead>
								<tr>
									<th>Account Name</th>
									<th>Type</th>
									<th>Status</th>
									<th class="text-right">Settled Balance</th>
									<th class="text-right">Pending Balance</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="acc in mappedAccounts" :key="acc.name">
									<td class="font-medium">{{ acc.name }}</td>
									<td class="text-sm text-light">{{ acc.type }}</td>
									<td>
										<span :class="['tag', acc.status === 'Retired' ? '' : 'green']">{{ acc.status }}</span>
									</td>
									<td class="text-right text-mono">{{ formatMinor(acc.settledMinor) }}</td>
									<td class="text-right text-mono text-light">{{ acc.pendingMinor === 0 ? "-" : formatMinor(acc.pendingMinor) }}</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

					<section v-else-if="currentStep === 6" class="step">
						<h2>Budget categories</h2>
						<p class="text-light">Review active and retired categories before continuing.</p>
						<div v-if="categoryProxyCoverageCount > 0" class="card preview-validation-card" :class="categoryProxyDriftCount > 0 ? 'preview-validation-card--warning' : ''">
							<div class="preview-validation-card__row">
								<span class="font-medium">Aspire proxy parity</span>
								<span class="tag" :class="categoryProxyDriftCount > 0 ? 'amber' : 'green'">
									{{ categoryProxyDriftCount > 0 ? `${categoryProxyDriftCount} drift rows` : 'Matched' }}
								</span>
							</div>
							<p class="text-xs text-light">
								Values in this step are computed from staged ledger/allocation rows and checked against Aspire dashboard proxies.
							</p>
						</div>

					<div>
						<h3 class="text-xs text-light">Active budgets</h3>
						<div class="card table-card">
							<table class="data-table">
								<thead>
									<tr>
										<th>Category</th>
										<th>Group</th>
										<th>Config</th>
										<th class="text-right">Configured Budget</th>
										<th class="text-right">Available</th>
										<th>Edit</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="cat in activeMappedCategories" :key="cat.name">
										<td class="font-medium">{{ cat.name }}</td>
										<td class="text-sm text-light">{{ cat.group }}</td>
									<td class="text-sm text-light">{{ cat.configLabel }}</td>
									<td class="text-right text-mono">{{ formatMinor(cat.configuredBudgetMinor) }}</td>
									<td class="text-right text-mono">
										<span class="tooltip-trigger" :data-tooltip="`Activity: ${formatMinor(cat.activityMinor)}\nBudgeted: ${formatMinor(cat.budgetedMinor)}`">
											{{ formatMinor(cat.availableMinor) }}
										</span>
										<span v-if="cat.hasProxyDrift" class="tag amber" style="margin-left: 0.5rem;">drift</span>
									</td>
									<td>
										<button type="button" class="edit-icon" @click="openCategoryEdit(cat)">✎</button>
									</td>
								</tr>
									<tr v-if="!activeMappedCategories.length">
										<td colspan="6" class="text-light">No active categories.</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>

					<div>
						<h3 class="text-xs text-light">Retired budgets</h3>
						<div class="card table-card">
						<table class="data-table">
							<thead>
								<tr>
									<th>Category</th>
									<th class="text-right">Configured Budget (Last)</th>
									<th class="text-right">Available Balance</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="cat in retiredMappedCategories" :key="cat.name">
									<td class="font-medium">{{ cat.name }}</td>
									<td class="text-right text-mono">{{ formatMinor(cat.configuredBudgetMinor) }}</td>
									<td class="text-right text-mono">{{ formatMinor(cat.availableMinor) }}</td>
								</tr>
								<tr v-if="!retiredMappedCategories.length">
									<td colspan="3" class="text-light">No retired categories.</td>
								</tr>
							</tbody>
						</table>
							</div>
						</div>

						<div v-if="categoryEditOpen" class="modal-backdrop" @click.self="closeCategoryEdit">
							<div class="destination-modal card" role="dialog" aria-modal="true">
								<div class="destination-modal__header">
									<div>
										<div class="destination-modal__eyebrow">Budget Category</div>
										<h3 class="destination-modal__title">Edit category</h3>
										<p class="text-sm text-light">Update name, group, and budget configuration.</p>
									</div>
									<button type="button" class="modal-close" @click="closeCategoryEdit">×</button>
								</div>

								<div class="destination-modal__content">
									<label class="field-label">Category name</label>
									<input v-model="categoryEditForm.name" type="text" class="field-input" />

									<label class="field-label">Group</label>
									<input v-model="categoryEditForm.group" type="text" class="field-input" />

									<div class="segmented" role="group" aria-label="Budget config">
										<button type="button" :class="['segmented__btn', categoryEditForm.goal_type === null ? 'is-active' : '']" @click="categoryEditForm.goal_type = null">None</button>
										<button type="button" :class="['segmented__btn', categoryEditForm.goal_type === 'recurring' ? 'is-active' : '']" @click="categoryEditForm.goal_type = 'recurring'">Recurring</button>
										<button type="button" :class="['segmented__btn', categoryEditForm.goal_type === 'target_date' ? 'is-active' : '']" @click="categoryEditForm.goal_type = 'target_date'">Target date</button>
									</div>

									<div v-if="categoryEditForm.goal_type === 'recurring'" class="form-grid">
										<label class="field-label">Frequency</label>
										<select v-model="categoryEditForm.goal_frequency" class="field-input">
											<option value="monthly">Monthly</option>
											<option value="quarterly">Quarterly</option>
											<option value="yearly">Yearly</option>
										</select>

										<label class="field-label">Amount</label>
										<input v-model.number="categoryEditForm.goal_amount" type="number" step="0.01" class="field-input" />

										<label class="field-label">Next due date (optional)</label>
										<input v-model="categoryEditForm.goal_target_date" type="date" class="field-input" />
									</div>

									<div v-else-if="categoryEditForm.goal_type === 'target_date'" class="form-grid">
										<label class="field-label">Target date</label>
										<input v-model="categoryEditForm.goal_target_date" type="date" class="field-input" />

										<label class="field-label">Target amount</label>
										<input v-model.number="categoryEditForm.goal_amount" type="number" step="0.01" class="field-input" />
										<div class="text-sm text-light">Estimated monthly contribution: <strong>{{ formatMinor(categoryEditEstimatedMonthlyMinor) }}</strong></div>
									</div>

									<p v-if="categoryEditError" class="form-panel__error">{{ categoryEditError }}</p>
								</div>

								<div class="destination-modal__footer">
									<button type="button" class="btn btn-tertiary" @click="closeCategoryEdit">Cancel</button>
									<button type="button" class="btn btn-primary" @click="saveCategoryEdit">Save Changes</button>
								</div>
							</div>
						</div>
					</section>

				<section v-else-if="currentStep === 7" class="step">
					<div class="step-heading-row">
						<div>
							<h2>Transfer Exceptions</h2>
							<p class="text-light">
								We auto-paired {{ transferAutoPairs }} transfers. Resolve {{ unresolvedTransferCount }} remaining exceptions.
							</p>
						</div>
						<div :class="['tag', unresolvedTransferCount === 0 ? 'green' : 'amber']">
							{{ unresolvedTransferCount === 0 ? "Resolved" : "Action Required" }}
						</div>
					</div>
					<div class="card table-card">
						<table class="data-table">
							<thead>
								<tr>
									<th></th>
									<th>Date</th>
									<th>Account</th>
									<th>Category</th>
									<th>Memo</th>
									<th class="text-right">Amount</th>
									<th>State</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="ex in transferExceptions" :key="ex.row_index" :class="isTransferResolved(ex.row_index) ? '' : 'row-warning'">
									<td>
										<input
											type="checkbox"
											v-model="transferSelection[ex.row_index]"
											:disabled="isTransferResolved(ex.row_index)"
										/>
									</td>
									<td class="text-sm text-mono text-light">{{ ex.transaction_date || "—" }}</td>
									<td class="text-sm font-medium">{{ ex.account_name || "—" }}</td>
									<td class="text-sm text-light">{{ ex.category_name || "—" }}</td>
									<td class="text-sm text-light">{{ ex.memo || "—" }}</td>
									<td class="text-right text-mono">{{ formatMinor(ex.amount_minor) }}</td>
									<td>
										<div v-if="isTransferResolved(ex.row_index)" class="transfer-state transfer-state--resolved">
											<span>{{ transferResolutionLabel(ex.row_index) }}</span>
											<button type="button" class="btn btn-tertiary" @click="undoTransferResolution(ex.row_index)">
												Undo
											</button>
										</div>
										<div v-else class="transfer-state">
											<select class="inline-select" v-model="transferPendingKind[ex.row_index]">
												<option value="opening_balance">Opening Balance</option>
												<option value="balance_adjustment">Balance Adjustment</option>
											</select>
											<button type="button" class="btn btn-secondary btn-compact" @click="resolveTransferAsSystem(ex.row_index)">
												Resolve
											</button>
										</div>
									</td>
								</tr>
								<tr v-if="!transferExceptions.length">
									<td colspan="7" class="text-light">No transfer exceptions.</td>
								</tr>
							</tbody>
						</table>
					</div>
					<div v-if="selectedTransferIds.length" class="transfer-action-bar">
						<span class="text-sm transfer-action-bar__count">{{ selectedTransferIds.length }} Transactions Selected</span>
						<button type="button" class="btn btn-primary btn-compact" :disabled="!canLinkSelectedTransfers" @click="linkSelectedTransfers">
							Link as Transfer
						</button>
					</div>
				</section>

				<section v-else-if="currentStep === 8" class="step">
					<h2>Link Overlapping Accounts</h2>
					<p class="text-light">Pair budget accounts with matching Aspire net worth entities to prevent double counting.</p>
					<div class="card table-card">
						<table class="data-table">
							<thead>
								<tr>
									<th>Budget Account</th>
									<th>Aspire Net Worth Account</th>
									<th>Reason</th>
									<th>Strategy</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="item in duplicateRows" :key="item.name">
									<td class="font-medium">{{ item.budgetAccount }}</td>
									<td class="text-sm text-light">{{ item.netWorthAccount }}</td>
									<td class="text-xs text-mono">{{ item.reason }}</td>
									<td>
										<select class="inline-select" :value="item.strategyChoice" @change="setDuplicateStrategy(item.netWorthAccount, $event.target.value)">
											<option value="merge">Merge (recommended)</option>
											<option value="legacy_only">Keep Legacy Marks Only</option>
										</select>
									</td>
								</tr>
								<tr v-if="!duplicateRows.length">
									<td colspan="4" class="text-light">No duplicate mappings detected.</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section v-else-if="currentStep === 9" class="step">
					<h2>Net Worth Accounts</h2>
					<p class="text-light">For remaining net worth entries, create destination accounts and set starting values. For investment accounts, include cash and holdings so performance starts from the right value.</p>
					<div class="card table-card" style="margin-bottom: 1rem;">
						<div class="destination-modal__content" style="padding: 1rem;">
							<label class="field-label">Cutover date</label>
							<input v-model="netWorthCutoverDate" class="field-input" type="date" />
							<p class="text-xs text-light">This cutover date applies to all net worth entities in this step.</p>
						</div>
					</div>
					<div class="summary-banner">
						<div class="summary-item">
							<div class="label">Last Reported Net Worth</div>
							<div class="value">{{ formatMinor(totalLegacyMinor) }}</div>
						</div>
						<div class="summary-item">
							<div class="label">Derived Net Worth</div>
							<div class="value">{{ formatMinor(totalMappedMinor) }}</div>
						</div>
						<div class="summary-item">
							<div class="label">Difference</div>
							<div class="value">{{ formatSignedMinor(totalMappedMinor - totalLegacyMinor) }}</div>
						</div>
					</div>

					<div v-for="row in netWorthRows" :key="row.name" class="migration-card">
						<div class="migration-header">
							<div>
								<strong>{{ row.name }}</strong>
								<span class="text-sm text-light"> Balance: {{ formatSignedMinor(row.lastBalanceMinor) }}</span>
							</div>
						<div class="migration-header__actions">
							<div class="classification-switch" role="group" aria-label="Classification">
								<span :class="['classification-switch__label', row.classification === 'asset' ? 'is-active' : '']">Asset</span>
								<button
									type="button"
									class="classification-switch__track"
									:aria-pressed="row.classification === 'debt'"
									@click="toggleDecisionClassification(row.name)"
								>
									<span :class="['classification-switch__thumb', row.classification === 'debt' ? 'is-debt' : '']"></span>
								</button>
								<span :class="['classification-switch__label', row.classification === 'debt' ? 'is-active' : '']">Debt</span>
							</div>
							<span class="tag" :class="row.matched ? 'green' : 'amber'">
								{{ row.matched ? "Matched" : "Unbalanced" }}
							</span>
							</div>
						</div>
						<div class="migration-body">
							<div v-for="dest in row.destinations" :key="dest.name" class="account-destination-row">
								<div>
									{{ dest.name }}
									<span class="text-xs text-light">{{ dest.account_class }}</span>
									<span v-if="dest.account_class === 'investment' && dest.holdings && dest.holdings.length" class="text-xs text-light">{{ dest.holdings.length }} positions</span>
								</div>
								<div class="text-mono">{{ formatSignedMinor(dest.starting_value_minor) }}</div>
							</div>
							<div v-if="!row.destinations.length" class="text-sm text-light">No destination accounts configured.</div>
							<button type="button" class="btn btn-secondary btn-compact btn-dashed" @click="openDestinationModal(row.name, 'create_type')">
								+ Add Destination Account
							</button>
						</div>
					</div>
					<div v-if="!netWorthRows.length" class="card text-light">No net worth entries were found in this dataset.</div>

					<div v-if="destinationModalOpen" class="modal-backdrop" @click.self="closeDestinationModal">
						<div :class="['destination-modal', 'card', destinationModalMode === 'create_type' ? 'destination-modal--type' : '']" role="dialog" aria-modal="true">
							<datalist id="destination-institutions">
								<option v-for="institution in institutionList" :key="institution" :value="institution"></option>
							</datalist>
							<div v-if="destinationModalMode === 'create_type'" class="destination-modal__type-step">
								<div class="destination-modal__type-header">
									<div class="destination-modal__eyebrow">Account Onboarding</div>
									<div class="destination-modal__dots" aria-hidden="true">
										<span class="destination-modal__dot destination-modal__dot--active"></span>
										<span class="destination-modal__dot"></span>
										<span class="destination-modal__dot"></span>
									</div>
								</div>
								<h3>Select Account Type</h3>
								<p class="text-sm text-light">Choose the category that best describes this {{ currentDestinationClassificationLabel.toLowerCase() }}.</p>
								<div class="destination-type-grid">
									<button
										v-for="option in destinationTypeOptionsForCurrentRow"
										:key="option.id"
										type="button"
										:class="['destination-type-tile', destinationModalSelectedType === option.id ? 'destination-type-tile--selected' : '']"
										@click="destinationModalSelectedType = option.id"
									>
										<span class="destination-type-tile__label">{{ option.label }}</span>
										<span class="destination-type-tile__hint">{{ option.hint }}</span>
									</button>
								</div>
								<div class="destination-modal__footer">
									<button type="button" class="btn btn-tertiary" @click="closeDestinationModal">Back</button>
									<button type="button" class="btn btn-primary" :disabled="!destinationModalSelectedType" @click="startDestinationTypeFlow">
										Next
									</button>
								</div>
							</div>

							<template v-else>
								<div class="destination-modal__header">
									<div>
										<h3>Destination account setup</h3>
										<p class="text-sm text-light">{{ destinationModalName }} migration setup.</p>
									</div>
									<button type="button" class="btn btn-tertiary" @click="closeDestinationModal">Close</button>
								</div>
								<div class="destination-modal__progress">
									<div>
										<div class="destination-modal__eyebrow">Step {{ destinationModalStepIndex }} of {{ destinationModalSteps.length }}</div>
										<h4>{{ destinationModalStepTitle }}</h4>
										<p class="text-sm text-light">{{ destinationModalStepDescription }}</p>
									</div>
									<div class="destination-modal__dots" aria-hidden="true">
										<span
											v-for="(step, index) in destinationModalSteps"
											:key="step"
											:class="['destination-modal__dot', index < destinationModalStepIndex ? 'destination-modal__dot--active' : '']"
										></span>
									</div>
								</div>

										<div class="destination-modal__summary text-sm">
											<span>Aspire reported value:</span>
												<strong class="text-mono">{{ formatSignedMinor(destinationModalTargetMinor) }}</strong>
												<span class="tooltip-trigger" :data-tooltip="'This is the derived opening value that will be applied at cutover (cash + holdings for investments).'">
													Modeled cutover value:
												</span>
												<strong class="text-mono">{{ formatSignedMinor(destinationModalTotalMinor) }}</strong>
												<span>Difference:</span>
											<strong class="text-mono">{{ formatSignedMinor(destinationModalTotalMinor - destinationModalTargetMinor) }}</strong>
										</div>

								<div class="destination-modal__body">
									<div
										v-for="(dest, destinationIndex) in destinationModalDestinations"
										:key="`${dest.name}-${destinationIndex}`"
										class="destination-card"
									>
										<div class="destination-card__header">
											<div>
												<strong>{{ dest.name }}</strong>
												<div class="text-xs text-light">{{ destinationDisplayClassLabel(dest) }} / {{ dest.account_type }}</div>
											</div>
											<div class="text-right text-sm">
												<div class="text-xs text-light">{{ destinationValueLabel(dest) }}</div>
												<strong class="text-mono">{{ formatSignedMinor(destinationValuePreviewMinor(dest)) }}</strong>
											</div>
										</div>

										<div v-if="destinationModalStage === 'details'" class="destination-stage destination-stage--details">
											<div class="destination-form-grid">
												<label class="destination-field">
													<span>Account name</span>
													<input v-model="dest.name" type="text" class="inline-input" />
												</label>
												<label class="destination-field">
													<span>Institution</span>
													<input
														v-model="dest.institution_name"
														type="text"
														list="destination-institutions"
														class="inline-input"
														placeholder="Select or type..."
													/>
												</label>
												<label v-if="dest.account_class === 'investment'" class="destination-field">
													<span>Tax status</span>
													<select v-model="dest.tax_classification" class="inline-select destination-select">
														<option value="">Select tax status</option>
														<option v-for="option in investmentTaxOptions" :key="option" :value="option">{{ option }}</option>
													</select>
												</label>
												<label v-if="dest.account_class === 'investment'" class="destination-field destination-field--checkbox">
													<input v-model="dest.is_self_directed" type="checkbox" />
													<div>
														<span>Self-managed account</span>
														<small class="text-light">Use this when you choose the investments yourself.</small>
													</div>
												</label>
												<label v-else class="destination-field">
													<span>{{ destinationValueLabel(dest) }}</span>
													<input v-model="dest.starting_value_input" type="number" step="0.01" class="inline-number" />
												</label>
												<label v-if="dest.account_class === 'loan'" class="destination-field">
													<span>Original principal</span>
													<input v-model="dest.original_principal_input" type="number" step="0.01" class="inline-number" placeholder="Optional" />
												</label>
												<label v-if="dest.account_class === 'loan'" class="destination-field">
													<span>Interest rate (APY %)</span>
													<input v-model.number="dest.interest_rate_apy" type="number" step="0.01" class="inline-number" placeholder="Optional" />
												</label>
												<label v-if="dest.account_class === 'tangible'" class="destination-field">
													<span>Valuation source</span>
													<input v-model="dest.valuation_source" type="text" class="inline-input" placeholder="Appraisal, Zestimate, dealer estimate..." />
												</label>
												<label v-if="dest.account_class === 'tangible'" class="destination-field destination-field--full">
													<span>Notes</span>
													<input v-model="dest.note" type="text" class="inline-input" placeholder="Optional" />
												</label>
											</div>
											<p v-if="dest.account_class === 'investment'" class="destination-stage__note text-light">Next you will enter aggregate holdings for this account, one row per ticker.</p>
										</div>

										<div v-else-if="destinationModalStage === 'holdings' && dest.account_class === 'investment'" class="destination-stage">
											<div class="destination-holdings__header">
												<div>
													<h5>Holdings</h5>
													<p class="text-sm text-light">Enter aggregate positions, not individual tax lots. Prices fill in automatically as you add tickers.</p>
												</div>
												<span v-if="holdingQuoteLookupPending" class="text-xs text-light">Updating prices...</span>
											</div>
											<label class="destination-field">
												<span>Statement cash</span>
												<input v-model="dest.statement_cash_input" type="number" step="0.01" class="inline-number" />
											</label>
											<div class="destination-holdings__stats">
												<div class="holding-card__metric">
													<span>Statement cash</span>
													<strong>{{ formatMinor(investmentCashMinor(dest)) }}</strong>
												</div>
												<div class="holding-card__metric">
													<span>Holdings value</span>
													<strong>{{ formatMinor(destinationHoldingsMarketMinor(dest)) }}</strong>
												</div>
												<div class="holding-card__metric">
													<span>Modeled cutover</span>
													<strong>{{ formatSignedMinor(destinationDerivedStartingMinor(dest)) }}</strong>
												</div>
											</div>
											<div v-if="!dest.holdings.length" class="destination-holdings__empty text-light">No holdings yet. Add each ticker once with your total quantity and average cost basis.</div>
											<div v-for="(holding, lotIndex) in dest.holdings" :key="holding.id" class="holding-card">
												<div class="holding-card__header">
													<div>
														<strong>{{ holding.ticker || `Holding ${lotIndex + 1}` }}</strong>
														<p class="text-xs text-light">Aggregate position entry</p>
													</div>
													<button type="button" class="btn btn-tertiary btn-compact" @click="removeHolding(destinationIndex, lotIndex)">Remove</button>
												</div>
												<div class="holding-card__grid">
													<label>
														Ticker
														<input v-model="holding.ticker" type="text" class="inline-input" placeholder="VTI" @input="queueDestinationHoldingQuoteRefresh()" @blur="queueDestinationHoldingQuoteRefresh({ immediate: true })" />
													</label>
													<label>
														Quantity
														<input v-model.number="holding.quantity" type="number" step="0.0001" class="inline-number" />
													</label>
													<label>
														Avg cost basis
														<input v-model="holding.avg_cost_input" type="number" step="0.01" class="inline-number" />
													</label>
													<div class="holding-card__metric">
														<span>Market price</span>
														<strong>{{ holding.current_price_dollars ? formatMinor(minorFromDollars(holding.current_price_dollars)) : '—' }}</strong>
													</div>
													<div class="holding-card__metric">
														<span>Position value</span>
														<strong>{{ formatMinor(holdingTotalMinor(holding)) }}</strong>
													</div>
													<div class="holding-card__metric">
														<span>Cost basis total</span>
														<strong>{{ formatMinor(holdingCostBasisTotalMinor(holding)) }}</strong>
													</div>
												</div>
											</div>
											<div class="destination-investment__footer">
												<button type="button" class="btn btn-secondary btn-compact" @click="addHolding(destinationIndex)">Add holding</button>
											</div>
										</div>

										<div v-else-if="destinationModalStage === 'review'" class="destination-stage destination-stage--review">
											<div class="destination-review-grid">
												<div class="destination-review-item">
													<span>Account name</span>
													<strong>{{ dest.name }}</strong>
												</div>
												<div class="destination-review-item">
													<span>Institution</span>
													<strong>{{ dest.institution_name || '—' }}</strong>
												</div>
												<div class="destination-review-item">
													<span>Account type</span>
													<strong>{{ destinationDisplayClassLabel(dest) }}</strong>
												</div>
												<div class="destination-review-item">
													<span>Cutover value</span>
													<strong>{{ formatSignedMinor(destinationValuePreviewMinor(dest)) }}</strong>
												</div>
												<div v-if="dest.account_class === 'investment'" class="destination-review-item">
													<span>Tax status</span>
													<strong>{{ dest.tax_classification }}</strong>
												</div>
												<div v-if="dest.account_class === 'investment'" class="destination-review-item">
													<span>Management</span>
													<strong>{{ dest.is_self_directed ? 'Self-managed' : 'Advisor-managed / employer-managed' }}</strong>
												</div>
												<div v-if="dest.account_class === 'investment'" class="destination-review-item">
													<span>Holdings entered</span>
													<strong>{{ dest.holdings.length }}</strong>
												</div>
												<div v-if="dest.account_class === 'investment'" class="destination-review-item">
													<span>Statement cash</span>
													<strong>{{ formatMinor(investmentCashMinor(dest)) }}</strong>
												</div>
											</div>
											<div v-if="dest.account_class === 'investment' && dest.holdings.length" class="destination-review-holdings">
												<div v-for="holding in dest.holdings" :key="holding.id" class="destination-review-holding">
													<strong>{{ holding.ticker }}</strong>
													<span>{{ holding.quantity }} shares</span>
													<span>{{ formatMinor(holdingTotalMinor(holding)) }}</span>
												</div>
											</div>
										</div>
									</div>
								</div>

								<div class="destination-modal__footer">
									<button type="button" class="btn btn-tertiary" @click="goToPreviousDestinationStage">{{ destinationModalStepIndex === 1 ? 'Cancel' : 'Back' }}</button>
									<button v-if="!destinationModalAtReview" type="button" class="btn btn-primary" @click="goToNextDestinationStage">Next</button>
									<button v-else type="button" class="btn btn-primary" :disabled="destinationModalSaving" @click="applyDestinationModal">
										{{ destinationModalSaving ? "Saving..." : "Finish" }}
									</button>
								</div>
							</template>
						</div>
					</div>
				</section>

				<section v-else-if="currentStep === 10" class="step">
					<h2>Preview Migration</h2>
					<p class="text-light">Compare Aspire marks and Dojo-derived net worth before applying migration.</p>
					<div class="card preview-validation-card">
						<div class="preview-validation-card__row">
							<span class="font-medium">Transfer exceptions resolved</span>
							<span :class="['tag', unresolvedTransferCount === 0 ? 'green' : 'amber']">
								{{ unresolvedTransferCount === 0 ? "Pass" : `${unresolvedTransferCount} open` }}
							</span>
						</div>
					<p class="text-xs text-light">Apply is blocked until all orphan transfer legs are resolved.</p>
				</div>
				<div
					v-if="budgetParityMismatchBlocked"
					class="card preview-validation-card preview-validation-card--warning"
				>
					<div class="preview-validation-card__row">
						<span class="font-medium">Budget parity acknowledgment required</span>
						<span class="tag amber">Review</span>
					</div>
					<p class="text-xs text-light">
						Budget parity has expected semantic drift. Confirm the documented reason before finishing.
					</p>
					<label class="checkbox-row">
						<input v-model="budgetParityAcknowledged" type="checkbox" />
						<span>I understand this import includes a documented budget semantic difference.</span>
					</label>
					<label class="field-label" for="budget-parity-difference">Documented difference</label>
					<select
						id="budget-parity-difference"
						v-model="budgetParitySemanticDifference"
						class="field-input"
					>
						<option
							v-for="difference in budgetParityKnownDifferences"
							:key="difference"
							:value="difference"
						>
							{{ difference }}
						</option>
					</select>
				</div>
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
					<p class="text-light">Your Aspire data is now in Dojo. Open the dashboard to review follow-up tasks and reconciliations.</p>
					<button type="button" class="btn btn-primary success-cta" @click="goDashboard">Go to Dashboard</button>
				</section>
			</div>

			<div v-if="!isExtracting && currentStep > 1 && currentStep < totalSteps" class="wizard-footer">
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
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../services/api.js";

const router = useRouter();
const route = useRoute();

const WIZARD_STORAGE_KEY = "dojo-aspire-onboarding-v1";

const totalSteps = 11;
const stepTitles = [
	"Welcome",
	"Connect",
	"Source",
	"Overview",
	"Accounts",
	"Categories",
	"Transfers",
	"Linking",
	"Net Worth",
	"Preview",
	"Finish",
];
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
const netWorthCutoverDate = ref("");
const previewResult = ref(null);
const applyResult = ref(null);
const budgetParityAcknowledged = ref(false);
const budgetParitySemanticDifference = ref("month_rollover_overspending");
const destinationModalName = ref("");
const destinationModalDestinations = ref([]);
const destinationModalSaving = ref(false);
const destinationModalMode = ref("edit");
const destinationModalSelectedType = ref("");
const destinationModalStage = ref("details");
const holdingQuoteLookupPending = ref(false);

const investmentTaxOptions = [
	"Taxable Brokerage",
	"Traditional IRA",
	"Roth IRA",
	"401k",
	"403b",
	"529",
];

const institutionList = [
	"Chase",
	"Bank of America",
	"Wells Fargo",
	"Citigroup",
	"American Express",
	"Vanguard",
	"Fidelity",
	"Charles Schwab",
	"Capital One",
	"Discover",
	"USAA",
	"Navy Federal Credit Union",
	"PNC Bank",
	"TD Bank",
	"Goldman Sachs",
	"Morgan Stanley",
	"Interactive Brokers",
	"E*TRADE",
	"Robinhood",
	"Coinbase",
	"SoFi",
	"Ally Bank",
];

const destinationTypeOptions = [
	{
		id: "cash_checking",
		label: "Cash & Checking",
		hint: "Bank cash that should carry a direct ledger balance.",
		account_class: "cash",
		account_type: "asset",
		classification: "asset",
	},
	{
		id: "savings_cd",
		label: "Savings / CD",
		hint: "Accessible savings, CDs, and other interest-bearing cash assets.",
		account_class: "accessible",
		account_type: "asset",
		classification: "asset",
	},
	{
		id: "investment",
		label: "Investment",
		hint: "Brokerages, IRAs, 401(k)s, and other market-priced portfolios.",
		account_class: "investment",
		account_type: "asset",
		classification: "asset",
	},
	{
		id: "credit_card",
		label: "Credit Card",
		hint: "Revolving card balances and other short-term debt.",
		account_class: "credit",
		account_type: "liability",
		classification: "debt",
	},
	{
		id: "loan",
		label: "Loan",
		hint: "Mortgages, auto loans, student loans, and installment debt.",
		account_class: "loan",
		account_type: "liability",
		classification: "debt",
	},
	{
		id: "tangible_asset",
		label: "Tangible Asset",
		hint: "Homes, vehicles, collectibles, and other manually valued assets.",
		account_class: "tangible",
		account_type: "asset",
		classification: "asset",
	},
];

const transferDraft = reactive({});
const transferSelection = reactive({});
const transferPendingKind = reactive({});

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
	mutationFn: (payload) => api.aspire.apply(payload),
	onSuccess: async (result) => {
		applyResult.value = result;
		await statusQuery.refetch();
	},
});

const budgetParityKnownDifferences = computed(() => {
	const known = previewResult.value?.budget_parity_known_differences;
	if (Array.isArray(known) && known.length > 0) {
		return known;
	}
	return ["month_rollover_overspending"];
});

const previewBlockers = computed(() => previewResult.value?.blockers || []);
const budgetParityMismatchBlocked = computed(() =>
	previewBlockers.value.includes("budget_parity_mismatch"),
);
const nonBudgetPreviewBlockers = computed(() =>
	previewBlockers.value.filter(
		(blocker) => blocker !== "budget_parity_mismatch",
	),
);

const mappedAccounts = computed(() => {
	const accounts = mappingData.value?.mapping?.accounts || {};
	return Object.entries(accounts).map(([aspireName, value]) => ({
		aspireName,
		name: value.dojo_name,
		type: value.display_type || value.account_class,
		status: value.is_active ? "Active" : "Retired",
		settledMinor: Number(value.current_balance_minor || 0),
		pendingMinor: Number(value.pending_balance_minor || 0),
	}));
});

const mappedCategories = computed(() => {
	const categories = mappingData.value?.mapping?.categories || {};
	const specialNames = new Set(
		Object.values(mappingData.value?.aspire_special_labels || {}).filter(
			Boolean,
		),
	);
	const accountNames = new Set(
		Object.keys(mappingData.value?.mapping?.accounts || {}),
	);
	return Object.entries(categories).map(([aspireName, value]) => ({
		aspireName,
		name: value.dojo_name,
		group: value.group_name,
		isActive: value.is_active,
		isDisplayRow:
			!specialNames.has(aspireName) &&
			!accountNames.has(aspireName) &&
			String(value.dojo_name || "").trim().length > 0,
		configLabel: value.config_label || goalConfigLabel(value),
		configuredBudgetMinor: Number(value.configured_budget_minor || 0),
		budgetedMinor: Number(value.budgeted_minor || 0),
		activityMinor: Number(value.activity_minor || 0),
		availableMinor: Number(value.available_minor || 0),
		proxyConfiguredBudgetMinor:
			value.proxy_configured_budget_minor === null ||
			value.proxy_configured_budget_minor === undefined
				? null
				: Number(value.proxy_configured_budget_minor),
		proxyBudgetedMinor:
			value.proxy_budgeted_minor === null ||
			value.proxy_budgeted_minor === undefined
				? null
				: Number(value.proxy_budgeted_minor),
		proxyActivityMinor:
			value.proxy_activity_minor === null ||
			value.proxy_activity_minor === undefined
				? null
				: Number(value.proxy_activity_minor),
		proxyAvailableMinor:
			value.proxy_available_minor === null ||
			value.proxy_available_minor === undefined
				? null
				: Number(value.proxy_available_minor),
		driftConfiguredBudgetMinor:
			value.drift_configured_budget_minor === null ||
			value.drift_configured_budget_minor === undefined
				? null
				: Number(value.drift_configured_budget_minor),
		driftBudgetedMinor:
			value.drift_budgeted_minor === null ||
			value.drift_budgeted_minor === undefined
				? null
				: Number(value.drift_budgeted_minor),
		driftActivityMinor:
			value.drift_activity_minor === null ||
			value.drift_activity_minor === undefined
				? null
				: Number(value.drift_activity_minor),
		driftAvailableMinor:
			value.drift_available_minor === null ||
			value.drift_available_minor === undefined
				? null
				: Number(value.drift_available_minor),
		hasProxyCoverage:
			value.proxy_configured_budget_minor !== undefined ||
			value.proxy_budgeted_minor !== undefined ||
			value.proxy_activity_minor !== undefined ||
			value.proxy_available_minor !== undefined,
		hasProxyDrift:
			Number(value.drift_configured_budget_minor || 0) !== 0 ||
			Number(value.drift_budgeted_minor || 0) !== 0 ||
			Number(value.drift_activity_minor || 0) !== 0 ||
			Number(value.drift_available_minor || 0) !== 0,
	}));
});

const activeMappedCategories = computed(() =>
	mappedCategories.value.filter(
		(category) => category.isDisplayRow && category.isActive,
	),
);

const retiredMappedCategories = computed(() =>
	mappedCategories.value.filter(
		(category) => category.isDisplayRow && !category.isActive,
	),
);

const categoryProxyCoverageCount = computed(
	() => mappingData.value?.category_proxy_coverage_count || 0,
);
const categoryProxyDriftCount = computed(
	() =>
		activeMappedCategories.value.filter((category) => category.hasProxyDrift)
			.length,
);

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

const transferExceptionByIndex = computed(() => {
	const rows = {};
	for (const row of transferExceptions.value) {
		rows[row.row_index] = row;
	}
	return rows;
});

const unresolvedTransferCount = computed(() => {
	let count = 0;
	for (const row of transferExceptions.value) {
		if (!transferDraft[row.row_index]) {
			count += 1;
		}
	}
	return count;
});

const selectedTransferIds = computed(() => {
	const selected = [];
	for (const row of transferExceptions.value) {
		if (transferSelection[row.row_index] && !transferDraft[row.row_index]) {
			selected.push(row.row_index);
		}
	}
	return selected;
});

const canLinkSelectedTransfers = computed(() => {
	if (selectedTransferIds.value.length !== 2) {
		return false;
	}
	const [a, b] = selectedTransferIds.value;
	const first = transferExceptionByIndex.value[a];
	const second = transferExceptionByIndex.value[b];
	if (!first || !second) {
		return false;
	}
	if (
		first.account_name &&
		second.account_name &&
		first.account_name === second.account_name
	) {
		return false;
	}
	return Number(first.amount_minor || 0) === -Number(second.amount_minor || 0);
});

watch(transferExceptions, (rows) => {
	const savedResolutions = transfersData.value?.saved_resolutions || {};
	rows.forEach((row) => {
		if (!transferPendingKind[row.row_index]) {
			transferPendingKind[row.row_index] = "opening_balance";
		}
		if (transferSelection[row.row_index] === undefined) {
			transferSelection[row.row_index] = false;
		}

		const saved =
			savedResolutions[row.row_index] ||
			savedResolutions[String(row.row_index)];
		if (saved?.kind && !transferDraft[row.row_index]) {
			transferDraft[row.row_index] = {
				kind: saved.kind,
				linked_row_index:
					typeof saved.linked_row_index === "number"
						? saved.linked_row_index
						: null,
			};
		}
	});
});

const isTransferResolved = (rowIndex) => Boolean(transferDraft[rowIndex]);

const transferResolutionLabel = (rowIndex) => {
	const resolution = transferDraft[rowIndex];
	if (!resolution) {
		return "Open";
	}
	if (resolution.kind === "linked") {
		return `Linked with #${resolution.linked_row_index}`;
	}
	if (resolution.kind === "opening_balance") {
		return "Opening Balance";
	}
	if (resolution.kind === "balance_adjustment") {
		return "Balance Adjustment";
	}
	return "Resolved";
};

const resolveTransferAsSystem = (rowIndex) => {
	const kind = transferPendingKind[rowIndex] || "opening_balance";
	transferDraft[rowIndex] = { kind, linked_row_index: null };
	transferSelection[rowIndex] = false;
};

const linkSelectedTransfers = () => {
	if (!canLinkSelectedTransfers.value) {
		globalError.value =
			"Select exactly two unresolved rows with matching opposite amounts in different accounts.";
		return;
	}
	const [first, second] = selectedTransferIds.value;
	transferDraft[first] = { kind: "linked", linked_row_index: second };
	transferDraft[second] = { kind: "linked", linked_row_index: first };
	transferSelection[first] = false;
	transferSelection[second] = false;
};

const undoTransferResolution = (rowIndex) => {
	const resolution = transferDraft[rowIndex];
	if (!resolution) {
		return;
	}
	if (
		resolution.kind === "linked" &&
		typeof resolution.linked_row_index === "number"
	) {
		delete transferDraft[resolution.linked_row_index];
		transferSelection[resolution.linked_row_index] = false;
	}
	delete transferDraft[rowIndex];
	transferSelection[rowIndex] = false;
};

const duplicateRows = computed(() => {
	const decisions = decisionsData.value?.decisions || {};
	return Object.entries(decisions)
		.filter(
			([, value]) =>
				value.decision === "duplicate_derive_from_ledger" ||
				value.decision === "legacy_only",
		)
		.map(([name, value]) => ({
			name,
			budgetAccount: value.ledger_account_id || "—",
			netWorthAccount: name,
			reason: value.reason || "Normalized name exact match",
			strategy: value.strategy_label || "Merge",
			strategyChoice:
				value.decision === "legacy_only" ? "legacy_only" : "merge",
		}));
});

const setDuplicateStrategy = (netWorthAccount, strategyChoice) => {
	if (!decisionsData.value?.decisions?.[netWorthAccount]) {
		return;
	}
	if (strategyChoice === "legacy_only") {
		decisionsData.value.decisions[netWorthAccount].decision = "legacy_only";
		return;
	}
	decisionsData.value.decisions[netWorthAccount].decision =
		"duplicate_derive_from_ledger";
};

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

const inferClassification = (name, decision = null) => {
	if (
		decision?.classification === "asset" ||
		decision?.classification === "debt"
	) {
		return decision.classification;
	}
	const firstDestination = Array.isArray(decision?.destinations)
		? decision.destinations[0]
		: null;
	if (
		firstDestination?.account_type === "liability" ||
		firstDestination?.account_class === "loan"
	) {
		return "debt";
	}
	if (firstDestination?.account_type === "asset") {
		return "asset";
	}
	const lastBy = decisionsData.value?.last_reported_by_category_minor || {};
	return Number(lastBy[name] || 0) < 0 ? "debt" : "asset";
};

const netWorthRows = computed(() => {
	const decisions = decisionsData.value?.decisions || {};
	const lastBy = decisionsData.value?.last_reported_by_category_minor || {};
	return Object.entries(decisions)
		.filter(([, value]) => value.decision !== "duplicate_derive_from_ledger")
		.filter(([name, value]) => {
			const hasMark = Object.hasOwn(lastBy, name);
			const hasDestinations =
				Array.isArray(value.destinations) && value.destinations.length > 0;
			return hasMark || hasDestinations;
		})
		.map(([name, value]) => {
			const lastBalanceMinor = Number(lastBy[name] || 0);
			const destinations = value.destinations || [];
			const destinationTotal = destinations.reduce(
				(sum, d) => sum + Number(d.starting_value_minor || 0),
				0,
			);
			const matched = Math.abs(destinationTotal - lastBalanceMinor) < 1;
			const classification = inferClassification(name, value);
			return {
				name,
				classification,
				lastBalanceMinor,
				destinations,
				matched,
			};
		});
});

const destinationModalOpen = computed(() =>
	Boolean(destinationModalName.value),
);

const destinationModalTargetMinor = computed(() => {
	const lastBy = decisionsData.value?.last_reported_by_category_minor || {};
	return Number(lastBy[destinationModalName.value] || 0);
});

const currentDestinationClassification = computed(() => {
	if (!destinationModalName.value) {
		return "asset";
	}
	const decision = decisionsData.value?.decisions?.[destinationModalName.value];
	return inferClassification(destinationModalName.value, decision);
});

const currentDestinationClassificationLabel = computed(() =>
	currentDestinationClassification.value === "debt" ? "Debt" : "Asset",
);

const destinationTypeOptionsForCurrentRow = computed(() =>
	destinationTypeOptions.filter(
		(option) =>
			option.classification === currentDestinationClassification.value,
	),
);

const destinationModalShowsInvestmentHoldings = computed(() =>
	destinationModalDestinations.value.some(
		(destination) => destination.account_class === "investment",
	),
);

const destinationModalSteps = computed(() =>
	destinationModalShowsInvestmentHoldings.value
		? ["details", "holdings", "review"]
		: ["details", "review"],
);

const destinationModalStepIndex = computed(() => {
	const index = destinationModalSteps.value.indexOf(
		destinationModalStage.value,
	);
	return index >= 0 ? index + 1 : 1;
});

const destinationModalStepTitle = computed(() => {
	switch (destinationModalStage.value) {
		case "holdings":
			return "Holdings";
		case "review":
			return "Review";
		default:
			return "Account details";
	}
});

const destinationModalStepDescription = computed(() => {
	switch (destinationModalStage.value) {
		case "holdings":
			return "Capture aggregate positions once the account shell is configured.";
		case "review":
			return "Confirm the destination metadata and cutover valuation before saving.";
		default:
			return "Set the account identity and cutover settings before moving deeper into setup.";
	}
});

const destinationModalAtReview = computed(
	() => destinationModalStage.value === "review",
);

const destinationModalTotalMinor = computed(() =>
	destinationModalDestinations.value.reduce(
		(sum, destination) => sum + destinationDerivedStartingMinor(destination),
		0,
	),
);

function randomId(prefix = "id") {
	if (typeof crypto !== "undefined" && crypto.randomUUID) {
		return `${prefix}-${crypto.randomUUID()}`;
	}
	return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function minorFromDollars(value) {
	const num = Number(value || 0);
	if (!Number.isFinite(num)) {
		return 0;
	}
	return Math.round(num * 100);
}

function dollarsFromMinor(value) {
	return Number(value || 0) / 100;
}

function minorToInput(value) {
	return minorToInputWithFallback(value, "0.00");
}

function minorToInputWithFallback(value, fallback = "") {
	if (value === null || value === undefined) {
		return fallback;
	}
	return (Number(value) / 100).toFixed(2);
}

const guessDestinationType = (name, classification) => {
	const normalized = String(name || "")
		.trim()
		.toLowerCase();
	if (classification === "debt") {
		if (
			/(credit|card|visa|mastercard|amex|american express|discover)/.test(
				normalized,
			)
		) {
			return "credit_card";
		}
		return "loan";
	}
	if (/(checking|cash|wallet)/.test(normalized)) {
		return "cash_checking";
	}
	if (/(savings|cd|certificate|money market)/.test(normalized)) {
		return "savings_cd";
	}
	if (
		/(401k|403b|ira|brokerage|pension|retirement|roth|hsa)/.test(normalized)
	) {
		return "investment";
	}
	if (/(house|home|property|real estate|vehicle|car|boat)/.test(normalized)) {
		return "tangible_asset";
	}
	return "tangible_asset";
};

const guessInvestmentTaxClassification = (name) => {
	const normalized = String(name || "")
		.trim()
		.toLowerCase();
	if (normalized.includes("roth")) return "Roth IRA";
	if (normalized.includes("traditional ira") || /\bira\b/.test(normalized)) {
		return "Traditional IRA";
	}
	if (normalized.includes("401k")) return "401k";
	if (normalized.includes("403b")) return "403b";
	if (normalized.includes("529")) return "529";
	if (/(brokerage|taxable|investment)/.test(normalized))
		return "Taxable Brokerage";
	return "";
};

const guessSelfDirected = (taxClassification) =>
	taxClassification === "Traditional IRA" ||
	taxClassification === "Roth IRA" ||
	taxClassification === "Taxable Brokerage";

const normalizeHolding = (holding) => {
	const currentPriceMinor =
		holding?.current_price_minor !== null &&
		holding?.current_price_minor !== undefined
			? Number(holding.current_price_minor || 0)
			: Number(holding?.avg_cost_minor || 0);
	const costBasisTotalMinor =
		holding?.cost_basis_total_minor !== null &&
		holding?.cost_basis_total_minor !== undefined
			? Number(holding.cost_basis_total_minor)
			: null;
	const quantity = Number(holding?.quantity || 0);
	const derivedBasisMinor =
		costBasisTotalMinor === null && quantity > 0
			? Math.round(quantity * Number(holding?.avg_cost_minor || 0))
			: null;
	return {
		id: String(holding?.id || "") || randomId("holding"),
		ticker: String(holding?.ticker || "").trim(),
		quantity,
		current_price_dollars: dollarsFromMinor(currentPriceMinor),
		avg_cost_input: minorToInputWithFallback(
			quantity > 0
				? Math.round(
						(costBasisTotalMinor === null
							? derivedBasisMinor
							: costBasisTotalMinor) / quantity,
					)
				: Number(holding?.avg_cost_minor || 0),
			"",
		),
	};
};

const normalizeDestination = (destination) => ({
	id: String(destination?.id || "") || randomId("dest"),
	name: String(destination?.name || "Destination").trim() || "Destination",
	institution_name: String(destination?.institution_name || "").trim(),
	account_class: destination?.account_class || "tangible",
	account_type: destination?.account_type || "asset",
	starting_value_minor: Number(destination?.starting_value_minor || 0),
	starting_value_input: minorToInput(destination?.starting_value_minor),
	statement_cash_input: minorToInputWithFallback(
		destination?.statement_cash_minor,
		"",
	),
	holdings: Array.isArray(destination?.holdings)
		? destination.holdings.map((holding) => normalizeHolding(holding))
		: [],
	is_self_directed:
		destination?.is_self_directed === null ||
		destination?.is_self_directed === undefined
			? false
			: Boolean(destination.is_self_directed),
	tax_classification: destination?.tax_classification || "",
	interest_rate_apy:
		destination?.interest_rate_apy === null ||
		destination?.interest_rate_apy === undefined
			? null
			: Number(destination.interest_rate_apy),
	original_principal_minor:
		destination?.original_principal_minor === null ||
		destination?.original_principal_minor === undefined
			? null
			: Number(destination.original_principal_minor),
	original_principal_input: minorToInputWithFallback(
		destination?.original_principal_minor,
		"",
	),
	loan_mode: destination?.loan_mode || null,
	valuation_source: destination?.valuation_source || null,
	note: destination?.note || null,
});

const holdingCostBasisTotalMinor = (holding) => {
	const quantity = Number(holding?.quantity || 0);
	const avgCostMinor = minorFromDollars(holding?.avg_cost_input);
	return Math.round(quantity * avgCostMinor);
};

const holdingTotalMinor = (holding) => {
	const quantity = Number(holding?.quantity || 0);
	const priceMinor = minorFromDollars(holding?.current_price_dollars);
	return Math.round(quantity * priceMinor);
};

const destinationHoldingsMarketMinor = (destination) =>
	(destination?.holdings || []).reduce(
		(sum, holding) => sum + holdingTotalMinor(holding),
		0,
	);

const investmentCashMinor = (destination) =>
	minorFromDollars(destination?.statement_cash_input);

const destinationDerivedStartingMinor = (destination) => {
	if (destination.account_class !== "investment") {
		return minorFromDollars(destination.starting_value_input);
	}
	const holdingsTotal = (destination.holdings || []).reduce(
		(sum, holding) => sum + holdingTotalMinor(holding),
		0,
	);
	return holdingsTotal + investmentCashMinor(destination);
};

const destinationValuePreviewMinor = (destination) => {
	if (destination.account_class !== "investment") {
		return minorFromDollars(destination.starting_value_input);
	}
	return destinationDerivedStartingMinor(destination);
};

const buildDestinationFromType = (typeId, baseName) => {
	const type = destinationTypeOptions.find((option) => option.id === typeId);
	const seedMinor = destinationModalTargetMinor.value;
	const taxClassification =
		type?.account_class === "investment"
			? guessInvestmentTaxClassification(baseName)
			: "";
	if (!type) {
		return normalizeDestination({
			name: baseName,
			institution_name: "",
			account_class: "tangible",
			account_type: "asset",
			starting_value_minor: seedMinor,
		});
	}
	return normalizeDestination({
		name: baseName,
		institution_name: "",
		account_class: type.account_class,
		account_type: type.account_type,
		starting_value_minor: type.account_class === "investment" ? 0 : seedMinor,
		statement_cash_minor: type.account_class === "investment" ? 0 : null,
		holdings: type.account_class === "investment" ? [] : null,
		tax_classification: taxClassification,
		is_self_directed:
			type.account_class === "investment"
				? guessSelfDirected(taxClassification)
				: null,
	});
};

const openDestinationModal = (rowName, mode = "edit") => {
	const decision = decisionsData.value?.decisions?.[rowName];
	if (!decision) {
		return;
	}
	destinationModalName.value = rowName;
	destinationModalMode.value = mode;
	destinationModalSelectedType.value = guessDestinationType(
		rowName,
		inferClassification(rowName, decision),
	);

	if (mode === "create_type") {
		destinationModalDestinations.value = [];
		destinationModalStage.value = "details";
		return;
	}

	destinationModalDestinations.value = (decision.destinations || []).map(
		(destination) => normalizeDestination(destination),
	);
	if (!destinationModalDestinations.value.length) {
		destinationModalDestinations.value = [
			normalizeDestination({
				name: rowName,
				institution_name: "",
				account_class: "tangible",
				account_type: "asset",
				starting_value_minor: destinationModalTargetMinor.value,
			}),
		];
	}
	destinationModalStage.value = "details";
};

const closeDestinationModal = () => {
	destinationModalName.value = "";
	destinationModalDestinations.value = [];
	destinationModalSaving.value = false;
	destinationModalMode.value = "edit";
	destinationModalSelectedType.value = "";
	destinationModalStage.value = "details";
	if (holdingQuoteRefreshTimeoutId !== null) {
		window.clearTimeout(holdingQuoteRefreshTimeoutId);
		holdingQuoteRefreshTimeoutId = null;
	}
	holdingQuoteLookupPending.value = false;
};

const startDestinationTypeFlow = () => {
	if (!destinationModalSelectedType.value || !destinationModalName.value) {
		return;
	}
	destinationModalDestinations.value = [
		buildDestinationFromType(
			destinationModalSelectedType.value,
			destinationModalName.value,
		),
	];
	destinationModalMode.value = "edit";
	destinationModalStage.value = "details";
};

const destinationDisplayClassLabel = (destination) => {
	switch (destination?.account_class) {
		case "accessible":
			return "Savings / CD";
		case "credit":
			return "Credit Card";
		case "investment":
			return "Investment";
		case "loan":
			return "Loan";
		case "cash":
			return "Cash & Checking";
		default:
			return "Tangible Asset";
	}
};

const destinationValueLabel = (destination) => {
	if (
		destination?.account_class === "credit" ||
		destination?.account_class === "loan"
	) {
		return "Balance owed at cutover";
	}
	if (destination?.account_class === "investment") {
		return "Modeled value at cutover";
	}
	return "Value at cutover";
};

const validateDestinationDetails = () => {
	for (const destination of destinationModalDestinations.value) {
		if (!String(destination?.name || "").trim()) {
			throw new Error(
				"Each destination account needs a name before you continue.",
			);
		}
		if (
			destination?.account_class === "investment" &&
			!String(destination?.tax_classification || "").trim()
		) {
			throw new Error(
				"Select a tax status for each investment account before you continue.",
			);
		}
		if (destination?.account_class !== "investment") {
			const value = Number(destination?.starting_value_input);
			if (!Number.isFinite(value)) {
				throw new Error("Enter a valid cutover value before you continue.");
			}
		}
	}
};

const validateInvestmentHoldings = ({ requirePrices }) => {
	for (const destination of destinationModalDestinations.value) {
		if (destination?.account_class !== "investment") {
			continue;
		}
		for (const holding of destination.holdings || []) {
			const ticker = String(holding?.ticker || "").trim();
			const quantity = Number(holding?.quantity || 0);
			const avgCost = Number(holding?.avg_cost_input || 0);
			const rowTouched = ticker || quantity || avgCost;
			if (!rowTouched) {
				continue;
			}
			if (!ticker || !quantity || quantity <= 0 || !avgCost || avgCost <= 0) {
				throw new Error(
					"Each investment holding needs a ticker, a positive quantity, and a positive average cost basis.",
				);
			}
			if (requirePrices) {
				const price = Number(holding?.current_price_dollars || 0);
				if (!price || price <= 0) {
					throw new Error(
						`We could not fetch a market price for ${ticker}. Check the ticker symbol and try again.`,
					);
				}
			}
		}
	}
};

const goToPreviousDestinationStage = () => {
	const steps = destinationModalSteps.value;
	const currentIndex = steps.indexOf(destinationModalStage.value);
	if (currentIndex <= 0) {
		closeDestinationModal();
		return;
	}
	destinationModalStage.value = steps[currentIndex - 1];
};

const goToNextDestinationStage = async () => {
	globalError.value = "";
	try {
		validateDestinationDetails();
		if (destinationModalStage.value === "holdings") {
			await refreshDestinationHoldingQuotes();
			validateInvestmentHoldings({ requirePrices: true });
		}
		const steps = destinationModalSteps.value;
		const currentIndex = steps.indexOf(destinationModalStage.value);
		if (currentIndex < 0 || currentIndex >= steps.length - 1) {
			return;
		}
		destinationModalStage.value = steps[currentIndex + 1];
		if (destinationModalStage.value === "holdings") {
			queueDestinationHoldingQuoteRefresh({ immediate: true });
		}
	} catch (error) {
		globalError.value = userFacingError(
			error,
			"Complete the current step before moving on.",
		);
	}
};

let holdingQuoteRefreshTimeoutId = null;

const queueDestinationHoldingQuoteRefresh = ({ immediate = false } = {}) => {
	if (holdingQuoteRefreshTimeoutId !== null) {
		window.clearTimeout(holdingQuoteRefreshTimeoutId);
		holdingQuoteRefreshTimeoutId = null;
	}
	if (destinationModalStage.value !== "holdings") {
		return;
	}
	const tickers = destinationModalDestinations.value
		.flatMap((destination) => destination.holdings || [])
		.map((holding) =>
			String(holding?.ticker || "")
				.trim()
				.toUpperCase(),
		)
		.filter(Boolean);
	if (!tickers.length) {
		return;
	}
	if (immediate) {
		refreshDestinationHoldingQuotes().catch(() => {});
		return;
	}
	holdingQuoteRefreshTimeoutId = window.setTimeout(() => {
		holdingQuoteRefreshTimeoutId = null;
		refreshDestinationHoldingQuotes().catch(() => {});
	}, 350);
};

const refreshDestinationHoldingQuotes = async () => {
	const tickers = destinationModalDestinations.value
		.flatMap((destination) => destination.holdings || [])
		.map((holding) =>
			String(holding?.ticker || "")
				.trim()
				.toUpperCase(),
		)
		.filter(Boolean);
	if (!tickers.length) {
		return;
	}
	holdingQuoteLookupPending.value = true;
	try {
		const quotes = await api.investments.lookupQuotes(tickers);
		const byTicker = new Map(
			(quotes || []).map((quote) => [
				String(quote.ticker || "").toUpperCase(),
				quote,
			]),
		);
		for (const destination of destinationModalDestinations.value) {
			for (const holding of destination.holdings || []) {
				const ticker = String(holding?.ticker || "")
					.trim()
					.toUpperCase();
				if (!ticker) {
					continue;
				}
				const quote = byTicker.get(ticker);
				if (quote?.price_minor !== null && quote?.price_minor !== undefined) {
					holding.current_price_dollars = dollarsFromMinor(quote.price_minor);
				}
			}
		}
	} finally {
		holdingQuoteLookupPending.value = false;
	}
};

const addHolding = (destinationIndex) => {
	const destination = destinationModalDestinations.value[destinationIndex];
	if (!destination) {
		return;
	}
	if (!Array.isArray(destination.holdings)) {
		destination.holdings = [];
	}
	destination.holdings.push(
		normalizeHolding({
			id: randomId("holding"),
			ticker: "",
			quantity: 0,
			current_price_minor: 0,
			avg_cost_minor: 0,
		}),
	);
	queueDestinationHoldingQuoteRefresh();
};

const removeHolding = (destinationIndex, lotIndex) => {
	const destination = destinationModalDestinations.value[destinationIndex];
	if (!destination || !Array.isArray(destination.holdings)) {
		return;
	}
	destination.holdings.splice(lotIndex, 1);
	queueDestinationHoldingQuoteRefresh();
};

const applyDestinationModal = async () => {
	if (!destinationModalName.value || !decisionsData.value?.decisions) {
		closeDestinationModal();
		return;
	}
	const decision = decisionsData.value.decisions[destinationModalName.value];
	if (!decision) {
		closeDestinationModal();
		return;
	}

	destinationModalSaving.value = true;
	globalError.value = "";
	try {
		validateDestinationDetails();
		await refreshDestinationHoldingQuotes();
		validateInvestmentHoldings({ requirePrices: true });

		decision.cutover_date = netWorthCutoverDate.value || wizardTodayISO();
		decision.destinations = destinationModalDestinations.value.map(
			(destination) => {
				const accountClass =
					destination.account_class === "cash" ||
					destination.account_class === "accessible" ||
					destination.account_class === "credit" ||
					destination.account_class === "investment" ||
					destination.account_class === "loan" ||
					destination.account_class === "tangible"
						? destination.account_class
						: "tangible";
				const accountType =
					destination.account_type === "asset" ||
					destination.account_type === "liability"
						? destination.account_type
						: accountClass === "loan" || accountClass === "credit"
							? "liability"
							: "asset";

				const holdings =
					accountClass === "investment"
						? (destination.holdings || [])
								.map((holding) => normalizeHolding(holding))
								.filter((holding) => holding.ticker)
						: [];

				const statementCashMinor =
					accountClass === "investment"
						? investmentCashMinor(destination)
						: null;

				const startingValueMinor =
					accountClass === "investment"
						? destinationDerivedStartingMinor(destination)
						: minorFromDollars(destination.starting_value_input);

				const serializedHoldings =
					accountClass === "investment"
						? holdings.map((holding) => {
								const quantity = Number(holding.quantity || 0);
								const priceMinor = minorFromDollars(
									holding.current_price_dollars,
								);
								const rawAvgCostMinor = minorFromDollars(
									holding.avg_cost_input,
								);
								const costBasisTotalMinor = Math.round(
									quantity * rawAvgCostMinor,
								);
								const avgCostMinor =
									quantity > 0 ? Math.round(costBasisTotalMinor / quantity) : 0;
								return {
									ticker: holding.ticker,
									quantity,
									current_price_minor: priceMinor,
									cost_basis_total_minor: costBasisTotalMinor,
									avg_cost_minor: avgCostMinor,
								};
							})
						: [];

				return {
					name:
						String(destination.name || "Destination").trim() || "Destination",
					institution_name:
						String(destination.institution_name || "").trim() || null,
					account_class: accountClass,
					account_type: accountType,
					starting_value_minor: Number(startingValueMinor),
					statement_cash_minor: statementCashMinor,
					holdings: serializedHoldings,
					is_self_directed:
						accountClass === "investment"
							? Boolean(destination.is_self_directed)
							: null,
					tax_classification:
						accountClass === "investment"
							? String(destination.tax_classification || "").trim() || null
							: null,
					interest_rate_apy:
						accountClass === "loan" && destination.interest_rate_apy !== null
							? Number(destination.interest_rate_apy)
							: null,
					original_principal_minor:
						accountClass === "loan" && destination.original_principal_input
							? minorFromDollars(destination.original_principal_input)
							: null,
					loan_mode: accountClass === "loan" ? destination.loan_mode : null,
					valuation_source:
						accountClass === "tangible" ? destination.valuation_source : null,
					note: accountClass === "tangible" ? destination.note : null,
				};
			},
		);
		decision.decision = "track_forward";
		if (!decision.cutover_date) {
			decision.cutover_date = netWorthCutoverDate.value || wizardTodayISO();
		}

		await saveDecisions();
		closeDestinationModal();
	} catch (error) {
		globalError.value = userFacingError(
			error,
			"Unable to save destination account setup right now.",
		);
		destinationModalSaving.value = false;
	}
};

const totalLegacyMinor = computed(() => {
	return netWorthRows.value.reduce(
		(sum, row) => sum + Number(row.lastBalanceMinor || 0),
		0,
	);
});

const totalMappedMinor = computed(() => {
	return netWorthRows.value.reduce((sum, row) => {
		const destinationTotal = row.destinations.reduce(
			(sub, dest) => sub + Number(dest.starting_value_minor || 0),
			0,
		);
		return sum + destinationTotal;
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

const stepTitleLabel = computed(
	() => stepTitles[currentStep.value - 1] || `Step ${currentStep.value}`,
);

const validationBadgeLabel = computed(() => {
	if (globalError.value) {
		return "Blocked";
	}
	if (currentStep.value === 7 && unresolvedTransferCount.value > 0) {
		return "Needs Attention";
	}
	if (currentStep.value >= 10 && unresolvedTransferCount.value > 0) {
		return "Blocked";
	}
	if (currentStep.value >= 10 && nonBudgetPreviewBlockers.value.length) {
		return "Blocked";
	}
	if (
		currentStep.value >= 10 &&
		budgetParityMismatchBlocked.value &&
		!budgetParityAcknowledged.value
	) {
		return "Blocked";
	}
	return "Passing";
});

const validationBadgeClass = computed(() => {
	if (validationBadgeLabel.value === "Blocked") {
		return "validation-badge--blocked";
	}
	if (validationBadgeLabel.value === "Needs Attention") {
		return "validation-badge--warning";
	}
	return "validation-badge--passing";
});

const validationBadgeHint = computed(() => {
	if (validationBadgeLabel.value === "Blocked") {
		if (globalError.value) {
			return globalError.value;
		}
		if (currentStep.value >= 10 && unresolvedTransferCount.value > 0) {
			return "Resolve transfer exceptions before applying migration.";
		}
		if (nonBudgetPreviewBlockers.value.length) {
			return `Preview blockers: ${nonBudgetPreviewBlockers.value.join(", ")}`;
		}
		if (
			currentStep.value >= 10 &&
			budgetParityMismatchBlocked.value &&
			!budgetParityAcknowledged.value
		) {
			return "Acknowledge the documented budget parity semantic difference before finishing.";
		}
		return "Resolve blocking issues before finishing migration.";
	}
	if (validationBadgeLabel.value === "Needs Attention") {
		return "Resolve transfer exceptions to continue.";
	}
	return "Current step validations are passing.";
});

const primaryActionLabel = computed(() => {
	return currentStep.value === 10 ? "Finish" : "Continue";
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

function mergeMappingPreviewFields(localValue, remoteValue) {
	if (!localValue || !remoteValue) {
		return remoteValue || localValue;
	}
	const merged = {
		...remoteValue,
		...localValue,
		mapping_status: localValue.mapping_status || remoteValue.mapping_status,
		category_proxy_coverage_count:
			remoteValue.category_proxy_coverage_count || 0,
		category_proxy_drift_count: remoteValue.category_proxy_drift_count || 0,
		mapping: {
			...remoteValue.mapping,
			...localValue.mapping,
			accounts: {
				...(remoteValue.mapping?.accounts || {}),
				...(localValue.mapping?.accounts || {}),
			},
			categories: {
				...(remoteValue.mapping?.categories || {}),
				...(localValue.mapping?.categories || {}),
			},
		},
	};

	const localAccounts = localValue.mapping?.accounts || {};
	const remoteAccounts = remoteValue.mapping?.accounts || {};
	Object.keys(localAccounts).forEach((aspireName) => {
		const localAccount = localAccounts[aspireName];
		const remoteAccount = remoteAccounts[aspireName];
		if (!localAccount || !remoteAccount) {
			return;
		}
		localAccount.current_balance_minor = remoteAccount.current_balance_minor;
		localAccount.pending_balance_minor = remoteAccount.pending_balance_minor;
		localAccount.display_type = remoteAccount.display_type;
		if (!localAccount.account_class) {
			localAccount.account_class = remoteAccount.account_class;
		}
		if (!localAccount.account_role) {
			localAccount.account_role = remoteAccount.account_role;
		}
		if (localAccount.is_active === undefined) {
			localAccount.is_active = remoteAccount.is_active;
		}
	});

	const localCategories = localValue.mapping?.categories || {};
	const remoteCategories = remoteValue.mapping?.categories || {};
	Object.keys(localCategories).forEach((aspireName) => {
		const localCategory = localCategories[aspireName];
		const remoteCategory = remoteCategories[aspireName];
		if (!localCategory || !remoteCategory) {
			return;
		}
		localCategory.available_minor = remoteCategory.available_minor;
		localCategory.activity_minor = remoteCategory.activity_minor;
		localCategory.budgeted_minor = remoteCategory.budgeted_minor;
		localCategory.configured_budget_minor =
			remoteCategory.configured_budget_minor;
		localCategory.proxy_configured_budget_minor =
			remoteCategory.proxy_configured_budget_minor;
		localCategory.proxy_budgeted_minor = remoteCategory.proxy_budgeted_minor;
		localCategory.proxy_activity_minor = remoteCategory.proxy_activity_minor;
		localCategory.proxy_available_minor = remoteCategory.proxy_available_minor;
		localCategory.drift_configured_budget_minor =
			remoteCategory.drift_configured_budget_minor;
		localCategory.drift_budgeted_minor = remoteCategory.drift_budgeted_minor;
		localCategory.drift_activity_minor = remoteCategory.drift_activity_minor;
		localCategory.drift_available_minor = remoteCategory.drift_available_minor;
		localCategory.config_label = remoteCategory.config_label;
		if (
			localCategory.goal_type === undefined ||
			localCategory.goal_type === null
		) {
			localCategory.goal_type = remoteCategory.goal_type;
		}
		if (
			localCategory.goal_amount_minor === undefined ||
			localCategory.goal_amount_minor === null
		) {
			localCategory.goal_amount_minor = remoteCategory.goal_amount_minor;
		}
		if (
			localCategory.goal_target_date === undefined ||
			localCategory.goal_target_date === null
		) {
			localCategory.goal_target_date = remoteCategory.goal_target_date;
		}
		if (
			localCategory.goal_frequency === undefined ||
			localCategory.goal_frequency === null
		) {
			localCategory.goal_frequency = remoteCategory.goal_frequency;
		}
		if (!localCategory.group_name) {
			localCategory.group_name = remoteCategory.group_name;
		}
		if (!localCategory.dojo_name) {
			localCategory.dojo_name = remoteCategory.dojo_name;
		}
		if (localCategory.is_active === undefined) {
			localCategory.is_active = remoteCategory.is_active;
		}
	});

	return merged;
}

const loadMapping = async ({ force = false } = {}) => {
	if (mappingData.value && !force) {
		return;
	}
	const result = await api.aspire.getMapping();
	if (!mappingData.value) {
		mappingData.value = result;
		return;
	}
	mappingData.value = mergeMappingPreviewFields(mappingData.value, result);
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
	const activeRowIndexes = new Set(
		transferExceptions.value.map((row) => String(row.row_index)),
	);
	Object.entries(transferDraft).forEach(([rowIndex, value]) => {
		if (!activeRowIndexes.has(String(rowIndex)) || !value?.kind) {
			return;
		}
		resolutions[rowIndex] = {
			kind: value.kind,
			linked_row_index:
				typeof value.linked_row_index === "number"
					? value.linked_row_index
					: null,
		};
	});
	await saveTransfersMutation.mutateAsync({ resolutions });
};

const loadDecisions = async () => {
	const result = await api.aspire.getNetWorthDecisions();
	decisionsData.value = result;
	if (!netWorthCutoverDate.value) {
		netWorthCutoverDate.value = wizardTodayISO();
	}
	if (decisionsData.value?.decisions) {
		Object.entries(decisionsData.value.decisions).forEach(
			([name, decision]) => {
				if (
					decision.classification !== "asset" &&
					decision.classification !== "debt"
				) {
					decision.classification = inferClassification(name, decision);
				}
				if (decision.decision === "track_forward") {
					decision.cutover_date = netWorthCutoverDate.value;
				}
			},
		);
	}
};

watch(
	() => netWorthCutoverDate.value,
	(value) => {
		if (!value || !decisionsData.value?.decisions) {
			return;
		}
		Object.values(decisionsData.value.decisions).forEach((decision) => {
			if (decision.decision === "track_forward") {
				decision.cutover_date = value;
			}
		});
	},
);

const setDecisionClassification = (name, classification) => {
	if (!decisionsData.value?.decisions?.[name]) {
		return;
	}
	decisionsData.value.decisions[name].classification = classification;
};

const toggleDecisionClassification = (name) => {
	const current = inferClassification(
		name,
		decisionsData.value?.decisions?.[name],
	);
	setDecisionClassification(name, current === "debt" ? "asset" : "debt");
};

const saveDecisions = async () => {
	if (!decisionsData.value?.decisions) {
		return;
	}
	const normalized = {};
	Object.entries(decisionsData.value.decisions).forEach(([name, decision]) => {
		const rawCutover = decision.cutover_date;
		const cutover =
			typeof rawCutover === "string" && rawCutover.trim() ? rawCutover : null;
		normalized[name] = {
			...decision,
			cutover_date: cutover,
		};
	});
	await saveDecisionsMutation.mutateAsync({
		decisions: normalized,
		complete: true,
	});
};

const loadPreview = async () => {
	previewResult.value = await api.aspire.preview();
};

const runApply = async () => {
	applyResult.value = await applyMutation.mutateAsync({
		force: false,
		ack_budget_parity_mismatch: budgetParityMismatchBlocked.value
			? budgetParityAcknowledged.value
			: false,
		budget_parity_semantic_difference: budgetParityMismatchBlocked.value
			? budgetParitySemanticDifference.value
			: null,
	});
	clearLocalDraft();
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
			if (unresolvedTransferCount.value > 0) {
				globalError.value =
					"Resolve every transfer exception before continuing. Use Link as Transfer or a system resolution.";
				return;
			}
			await saveTransfers();
			await loadDecisions();
		}
		if (currentStep.value === 8) {
			await saveDecisions();
		}
		if (currentStep.value === 9) {
			if (destinationModalOpen.value) {
				globalError.value = "Close destination setup before continuing.";
				return;
			}
			await saveDecisions();
		}
		if (currentStep.value === 10) {
			if (!previewResult.value) {
				await loadPreview();
			}
			if (nonBudgetPreviewBlockers.value.length > 0) {
				globalError.value = `Resolve preview blockers before finishing: ${nonBudgetPreviewBlockers.value.join(", ")}`;
				return;
			}
			if (
				budgetParityMismatchBlocked.value &&
				!budgetParityAcknowledged.value
			) {
				globalError.value =
					"Acknowledge the documented budget parity semantic difference before finishing.";
				return;
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
	clearLocalDraft();
	router.push("/");
};

const categoryEditOpen = ref(false);
const categoryEditAspireName = ref("");
const categoryEditError = ref("");
const categoryEditForm = reactive({
	name: "",
	group: "",
	goal_type: null,
	goal_frequency: "monthly",
	goal_target_date: "",
	goal_amount: 0,
});

const currentBudgetMonthStart = computed(() => {
	const vToday = mappingData.value?.aspire_special_labels?.v_Today;
	if (typeof vToday === "string" && vToday) {
		const parsed = new Date(vToday);
		if (!Number.isNaN(parsed.getTime())) {
			return new Date(
				Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth(), 1),
			);
		}
	}
	const now = new Date();
	return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
});

function goalConfigLabel(mapping) {
	if (mapping?.goal_type === "target_date" && mapping?.goal_target_date) {
		return `Target date (${mapping.goal_target_date})`;
	}
	if (mapping?.goal_type === "recurring" && mapping?.goal_frequency) {
		return `Recurring (${mapping.goal_frequency})`;
	}
	return "-";
}

function monthsRemaining(fromMonthStart, targetDateISO) {
	const target = new Date(targetDateISO);
	if (Number.isNaN(target.getTime())) {
		return 0;
	}
	const startY = fromMonthStart.getUTCFullYear();
	const startM = fromMonthStart.getUTCMonth();
	const endY = target.getUTCFullYear();
	const endM = target.getUTCMonth();
	const diff = (endY - startY) * 12 + (endM - startM) + 1;
	return diff > 0 ? diff : 0;
}

function wizardTodayISO() {
	const vToday = mappingData.value?.aspire_special_labels?.v_Today;
	if (typeof vToday === "string" && /^\d{4}-\d{2}-\d{2}$/.test(vToday)) {
		return vToday;
	}
	return new Date().toISOString().slice(0, 10);
}

function configuredBudgetMinor(mapping, availableMinor) {
	if (!mapping?.goal_type) {
		return 0;
	}
	const goalAmountMinor = Number(mapping.goal_amount_minor || 0);
	if (goalAmountMinor <= 0) {
		return 0;
	}
	if (mapping.goal_type === "recurring") {
		const freq = mapping.goal_frequency || "monthly";
		if (freq === "monthly") return goalAmountMinor;
		if (freq === "quarterly") return Math.round(goalAmountMinor / 3);
		if (freq === "yearly") return Math.round(goalAmountMinor / 12);
		return goalAmountMinor;
	}
	if (mapping.goal_type === "target_date") {
		if (!mapping.goal_target_date) {
			return 0;
		}
		const remainingMonths = monthsRemaining(
			currentBudgetMonthStart.value,
			mapping.goal_target_date,
		);
		if (!remainingMonths) {
			return 0;
		}
		const currentAvailable = Math.max(Number(availableMinor || 0), 0);
		const remaining = Math.max(goalAmountMinor - currentAvailable, 0);
		if (!remaining) {
			return 0;
		}
		return Math.round(remaining / remainingMonths);
	}
	return 0;
}

const categoryEditEstimatedMonthlyMinor = computed(() => {
	if (categoryEditForm.goal_type !== "target_date") {
		return 0;
	}
	const mapping = {
		goal_type: "target_date",
		goal_target_date: categoryEditForm.goal_target_date,
		goal_amount_minor: Math.round(
			Number(categoryEditForm.goal_amount || 0) * 100,
		),
	};
	return configuredBudgetMinor(mapping, 0);
});

const openCategoryEdit = (cat) => {
	categoryEditError.value = "";
	const aspireName = cat?.aspireName;
	const record = mappingData.value?.mapping?.categories?.[aspireName];
	if (!record) {
		globalError.value = "Unable to edit this category.";
		return;
	}
	categoryEditAspireName.value = aspireName;
	categoryEditForm.name = record.dojo_name || aspireName;
	categoryEditForm.group = record.group_name || "Uncategorized";
	categoryEditForm.goal_type = record.goal_type || null;
	categoryEditForm.goal_frequency = record.goal_frequency || "monthly";
	categoryEditForm.goal_target_date = record.goal_target_date || "";
	categoryEditForm.goal_amount = Number(record.goal_amount_minor || 0) / 100;
	categoryEditOpen.value = true;
};

const closeCategoryEdit = () => {
	categoryEditOpen.value = false;
	categoryEditAspireName.value = "";
	categoryEditError.value = "";
};

const saveCategoryEdit = () => {
	categoryEditError.value = "";
	const aspireName = categoryEditAspireName.value;
	const record = mappingData.value?.mapping?.categories?.[aspireName];
	if (!record) {
		closeCategoryEdit();
		return;
	}
	const name = String(categoryEditForm.name || "").trim();
	if (!name) {
		categoryEditError.value = "Category name is required.";
		return;
	}
	const group = String(categoryEditForm.group || "").trim() || "Uncategorized";

	record.dojo_name = name;
	record.group_name = group;

	if (categoryEditForm.goal_type === null) {
		record.goal_type = null;
		record.goal_amount_minor = null;
		record.goal_target_date = null;
		record.goal_frequency = null;
		record.config_label = "-";
		record.configured_budget_minor = 0;
		closeCategoryEdit();
		return;
	}

	const amountMinor = Math.round(
		Number(categoryEditForm.goal_amount || 0) * 100,
	);
	if (amountMinor <= 0) {
		categoryEditError.value = "Goal amount must be greater than 0.";
		return;
	}

	if (categoryEditForm.goal_type === "recurring") {
		record.goal_type = "recurring";
		record.goal_amount_minor = amountMinor;
		record.goal_frequency = categoryEditForm.goal_frequency;
		record.goal_target_date = categoryEditForm.goal_target_date || null;
		record.config_label = goalConfigLabel(record);
		record.configured_budget_minor = configuredBudgetMinor(
			record,
			Number(record.available_minor || 0),
		);
		closeCategoryEdit();
		return;
	}

	if (categoryEditForm.goal_type === "target_date") {
		if (!categoryEditForm.goal_target_date) {
			categoryEditError.value = "Target date is required.";
			return;
		}
		record.goal_type = "target_date";
		record.goal_amount_minor = amountMinor;
		record.goal_target_date = categoryEditForm.goal_target_date;
		record.goal_frequency = null;
		record.config_label = goalConfigLabel(record);
		record.configured_budget_minor = configuredBudgetMinor(
			record,
			Number(record.available_minor || 0),
		);
		closeCategoryEdit();
		return;
	}
};

function clearLocalDraft() {
	if (typeof window === "undefined") {
		return;
	}
	window.localStorage.removeItem(WIZARD_STORAGE_KEY);
}

function loadLocalDraft() {
	if (typeof window === "undefined") {
		return;
	}
	const raw = window.localStorage.getItem(WIZARD_STORAGE_KEY);
	if (!raw) {
		return;
	}
	try {
		const parsed = JSON.parse(raw);
		if (
			typeof parsed.currentStep === "number" &&
			parsed.currentStep >= 1 &&
			parsed.currentStep <= totalSteps
		) {
			currentStep.value = parsed.currentStep;
		}
		if (typeof parsed.spreadsheet === "string") {
			spreadsheet.value = parsed.spreadsheet;
		}
		if (parsed.verifyResult && typeof parsed.verifyResult === "object") {
			verifyResult.value = parsed.verifyResult;
		}
		if (
			parsed.extractionSummary &&
			typeof parsed.extractionSummary === "object"
		) {
			extractionSummary.value = parsed.extractionSummary;
		}
		if (parsed.mappingData && typeof parsed.mappingData === "object") {
			mappingData.value = parsed.mappingData;
		}
		if (parsed.transfersData && typeof parsed.transfersData === "object") {
			transfersData.value = parsed.transfersData;
		}
		if (parsed.decisionsData && typeof parsed.decisionsData === "object") {
			decisionsData.value = parsed.decisionsData;
			if (decisionsData.value?.decisions) {
				Object.entries(decisionsData.value.decisions).forEach(
					([name, decision]) => {
						if (
							decision.classification !== "asset" &&
							decision.classification !== "debt"
						) {
							decision.classification = inferClassification(name, decision);
						}
					},
				);
			}
		}
		if (typeof parsed.netWorthCutoverDate === "string") {
			netWorthCutoverDate.value = parsed.netWorthCutoverDate;
		}
		if (parsed.previewResult && typeof parsed.previewResult === "object") {
			previewResult.value = parsed.previewResult;
		}
		if (typeof parsed.budgetParityAcknowledged === "boolean") {
			budgetParityAcknowledged.value = parsed.budgetParityAcknowledged;
		}
		if (typeof parsed.budgetParitySemanticDifference === "string") {
			budgetParitySemanticDifference.value =
				parsed.budgetParitySemanticDifference;
		}
		if (parsed.applyResult && typeof parsed.applyResult === "object") {
			applyResult.value = parsed.applyResult;
		}
		if (typeof parsed.destinationModalName === "string") {
			destinationModalName.value = parsed.destinationModalName;
		}
		if (parsed.destinationModalMode === "create_type") {
			destinationModalMode.value = "create_type";
		}
		if (typeof parsed.destinationModalSelectedType === "string") {
			destinationModalSelectedType.value = parsed.destinationModalSelectedType;
		}
		if (
			parsed.destinationModalDestinations &&
			Array.isArray(parsed.destinationModalDestinations)
		) {
			destinationModalDestinations.value =
				parsed.destinationModalDestinations.map((destination) =>
					normalizeDestination(destination),
				);
		}
		if (parsed.transferDraft && typeof parsed.transferDraft === "object") {
			Object.entries(parsed.transferDraft).forEach(([rowIndex, resolution]) => {
				if (!resolution || typeof resolution !== "object") {
					return;
				}
				const kind = resolution.kind;
				if (
					!["linked", "opening_balance", "balance_adjustment"].includes(kind)
				) {
					return;
				}
				transferDraft[rowIndex] = {
					kind,
					linked_row_index:
						typeof resolution.linked_row_index === "number"
							? resolution.linked_row_index
							: null,
				};
			});
		}
		if (
			parsed.transferPendingKind &&
			typeof parsed.transferPendingKind === "object"
		) {
			Object.entries(parsed.transferPendingKind).forEach(([rowIndex, kind]) => {
				if (["opening_balance", "balance_adjustment"].includes(kind)) {
					transferPendingKind[rowIndex] = kind;
				}
			});
		}
		if (
			parsed.transferSelection &&
			typeof parsed.transferSelection === "object"
		) {
			Object.entries(parsed.transferSelection).forEach(
				([rowIndex, selected]) => {
					transferSelection[rowIndex] = Boolean(selected);
				},
			);
		}
	} catch {
		clearLocalDraft();
	}
}

function saveLocalDraft() {
	if (typeof window === "undefined") {
		return;
	}
	const payload = {
		currentStep: currentStep.value,
		spreadsheet: spreadsheet.value,
		verifyResult: verifyResult.value,
		extractionSummary: extractionSummary.value,
		mappingData: mappingData.value,
		transfersData: transfersData.value,
		decisionsData: decisionsData.value,
		netWorthCutoverDate: netWorthCutoverDate.value,
		previewResult: previewResult.value,
		applyResult: applyResult.value,
		budgetParityAcknowledged: budgetParityAcknowledged.value,
		budgetParitySemanticDifference: budgetParitySemanticDifference.value,
		destinationModalName: destinationModalName.value,
		destinationModalMode: destinationModalMode.value,
		destinationModalSelectedType: destinationModalSelectedType.value,
		destinationModalDestinations: destinationModalDestinations.value,
		transferDraft,
		transferPendingKind,
		transferSelection,
	};
	window.localStorage.setItem(WIZARD_STORAGE_KEY, JSON.stringify(payload));
}

watch(
	[
		currentStep,
		spreadsheet,
		verifyResult,
		extractionSummary,
		mappingData,
		transfersData,
		decisionsData,
		previewResult,
		applyResult,
		budgetParityAcknowledged,
		budgetParitySemanticDifference,
		destinationModalName,
		destinationModalMode,
		destinationModalSelectedType,
		destinationModalDestinations,
		netWorthCutoverDate,
		transferDraft,
		transferPendingKind,
		transferSelection,
	],
	() => {
		saveLocalDraft();
	},
	{ deep: true },
);

onMounted(async () => {
	loadLocalDraft();
	if (!netWorthCutoverDate.value) {
		netWorthCutoverDate.value = wizardTodayISO();
	}
	if (decisionsData.value?.decisions) {
		Object.values(decisionsData.value.decisions).forEach((decision) => {
			if (decision.decision === "track_forward") {
				decision.cutover_date = netWorthCutoverDate.value;
			}
		});
	}
	if (currentStep.value === 5) {
		try {
			await loadMapping({ force: true });
		} catch {
			// ignore
		}
	}
	if (currentStep.value === 6) {
		try {
			await loadMapping({ force: true });
		} catch {
			// ignore
		}
	}
	if (
		currentStep.value >= 9 &&
		decisionsData.value &&
		decisionsData.value.last_reported_by_category_minor === undefined
	) {
		try {
			await loadDecisions();
		} catch {
			// ignore
		}
	}
});

watch(
	[currentStep, aspireActive],
	async ([step, isActive]) => {
		if (!isActive && !mappingData.value && !decisionsData.value) {
			return;
		}
		if (step === 5) {
			try {
				await loadMapping({ force: true });
			} catch {
				// ignore; step will show existing draft values
			}
		}
		if (step === 6) {
			try {
				await loadMapping({ force: true });
			} catch {
				// ignore; step will show existing draft values
			}
		}
		if (
			step >= 9 &&
			decisionsData.value &&
			decisionsData.value.last_reported_by_category_minor === undefined
		) {
			try {
				await loadDecisions();
			} catch {
				// ignore
			}
		}
	},
	{ immediate: true },
);

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

.wizard-header {
	display: block;
	margin-bottom: 0;
	padding: 1rem 0;
	border-bottom: 1px solid var(--border);
	background: var(--bg);
	flex-shrink: 0;
}

.wizard-header__row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 0.75rem;
}

.wizard-brand {
	display: flex;
	align-items: center;
	gap: 0.75rem;
}

.wizard-logo {
	font-family: var(--font-mono);
	font-size: 1.3rem;
	font-weight: 700;
	letter-spacing: 0.06em;
	text-transform: uppercase;
}

.wizard-context {
	font-family: var(--font-mono);
	font-size: 0.72rem;
	text-transform: uppercase;
	letter-spacing: 0.12em;
	color: var(--muted);
	padding-left: 0.8rem;
	border-left: 1px solid var(--border);
}

.wizard-step-label {
	font-family: var(--font-mono);
	font-size: 0.75rem;
	text-transform: uppercase;
	letter-spacing: 0.08em;
	color: var(--muted);
}

.wizard-step-meta {
	font-family: var(--font-mono);
	font-size: 0.74rem;
	color: var(--muted);
	letter-spacing: 0.04em;
}

.progress-bar {
	height: 2px;
	margin-top: 0.75rem;
	background: rgba(143, 124, 106, 0.3);
	position: relative;
	border-radius: 2px;
}

.progress-fill {
	position: absolute;
	left: 0;
	top: 0;
	height: 100%;
	background: #5f745f;
	transition: width 0.35s ease;
	border-radius: 2px;
}

.wizard-content {
	flex: 1;
	padding: 1rem 0 2.75rem;
}

.wizard-progress {
	margin-bottom: 1.5rem;
}

.wizard-progress__header {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 0.5rem;
}

.validation-badge {
	font-size: 0.72rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.06em;
	padding: 0.25rem 0.65rem;
	border-radius: 999px;
	border: 1px solid var(--border);
	display: inline-flex;
	align-items: center;
	gap: 0.35rem;
}

.validation-badge__info {
	font-size: 0.65rem;
	opacity: 0.8;
}

.validation-badge--passing {
	background: #e7f4e8;
	color: #2f6e35;
}

.validation-badge--warning {
	background: #fff5de;
	color: #8a6406;
}

.validation-badge--blocked {
	background: #fbe9e8;
	color: #8d2f2a;
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

.tile-icon {
	font-size: 1.7rem;
	line-height: 1;
	margin-bottom: 1rem;
	color: #9a9a9a;
}

.tile-icon--accent {
	color: #b79f84;
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
	background: #5f745f;
	color: #f7f5f2;
	border: 1px solid #5f745f;
}

.btn-primary:hover:not(:disabled) {
	transform: translateY(-1px);
	background: #506550;
	border-color: #506550;
}

.btn-glyph {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	margin-right: 0.45rem;
	font-weight: 700;
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

.tooltip-trigger {
	border-bottom: 1px dotted var(--muted);
	cursor: help;
	position: relative;
	display: inline-block;
}

.tooltip-trigger:hover::after {
	content: attr(data-tooltip);
	position: absolute;
	background: var(--text);
	color: #fff;
	padding: 0.45rem 0.55rem;
	border-radius: 4px;
	font-size: 0.72rem;
	white-space: pre-line;
	z-index: 30;
	transform: translate(-50%, -110%);
}

.edit-icon {
	border: 1px solid var(--border);
	background: transparent;
	border-radius: 4px;
	width: 28px;
	height: 28px;
	color: var(--text);
	cursor: pointer;
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

.btn-compact {
	height: 34px;
	padding: 0 0.65rem;
	font-size: 0.82rem;
}

.btn-dashed {
	width: 100%;
	border-style: dashed;
	margin-top: 0.35rem;
}

.transfer-state {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.transfer-state--resolved {
	justify-content: space-between;
}

.transfer-action-bar {
	display: flex;
	justify-content: center;
	align-items: center;
	gap: 0.75rem;
	margin-top: 0.55rem;
	background: #373737;
	color: #f5f5f5;
	padding: 0.6rem 0.9rem;
	border-radius: 999px;
	width: fit-content;
	margin-left: auto;
	margin-right: auto;
}

.transfer-action-bar__count {
	font-size: 0.9rem;
}

.transfer-action-bar .btn-primary {
	background: #f1f1f1;
	color: #2f2f2f;
	border-color: #f1f1f1;
	height: 32px;
}

.summary-banner {
	background: #f4f3f1;
	color: var(--text);
	padding: 1rem;
	border-radius: 4px;
	display: flex;
	justify-content: space-around;
	margin-bottom: 1rem;
	border: 1px solid var(--border);
}

.summary-item {
	text-align: center;
}

.summary-item .label {
	font-size: 0.68rem;
	text-transform: uppercase;
	letter-spacing: 0.07em;
	color: var(--muted);
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

.migration-header__actions {
	display: flex;
	align-items: center;
	gap: 0.6rem;
}

.classification-switch {
	display: inline-flex;
	align-items: center;
	gap: 0.45rem;
}

.classification-switch__label {
	font-size: 0.78rem;
	color: var(--muted);
	font-weight: 600;
}

.classification-switch__label.is-active {
	color: var(--text);
}

.classification-switch__track {
	position: relative;
	width: 44px;
	height: 24px;
	padding: 0;
	border: 1px solid var(--border);
	border-radius: 999px;
	background: #ece7df;
	cursor: pointer;
}

.classification-switch__thumb {
	position: absolute;
	top: 2px;
	left: 2px;
	width: 18px;
	height: 18px;
	border-radius: 999px;
	background: #2f6e35;
	transition: transform 0.16s ease, background 0.16s ease;
}

.classification-switch__thumb.is-debt {
	transform: translateX(20px);
	background: #8a6406;
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

.modal-backdrop {
	position: fixed;
	inset: 0;
	background: rgba(25, 25, 25, 0.45);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 60;
	padding: 1rem;
}

.destination-modal {
	width: min(980px, 100%);
	max-height: calc(100vh - 3rem);
	overflow: auto;
	padding: 1rem;
	background: var(--surface);
	border: 1px solid var(--border);
}

.destination-modal--type {
	width: min(600px, 90%);
	max-height: 90vh;
	border-radius: 8px;
}

.destination-modal__type-step {
	display: grid;
	gap: 0.8rem;
}

.destination-modal__type-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 0.8rem;
}

.destination-modal__eyebrow {
	font-size: 0.72rem;
	font-family: var(--font-mono);
	text-transform: uppercase;
	letter-spacing: 0.09em;
	color: var(--muted);
}

.destination-modal__dots {
	display: inline-flex;
	gap: 0.35rem;
}

.destination-modal__dot {
	width: 8px;
	height: 8px;
	border-radius: 999px;
	background: #d6cdc0;
}

.destination-modal__dot--active {
	background: #3b3b3b;
}

.destination-type-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 0.8rem;
	margin-top: 0.25rem;
	max-height: 290px;
	overflow-y: auto;
	padding-right: 0.25rem;
}

.destination-type-tile {
	border: 1px solid var(--border);
	background: #fff;
	color: var(--text);
	padding: 1rem;
	text-align: left;
	border-radius: 4px;
	min-height: 128px;
	display: flex;
	flex-direction: column;
	justify-content: space-between;
	gap: 0.5rem;
}

.destination-type-tile--selected {
	border-color: #5f7161;
	box-shadow: inset 0 0 0 1px #5f7161;
	background: #f4f7f2;
}

.destination-type-tile__label {
	font-weight: 700;
	font-size: 1rem;
}

.destination-type-tile__hint {
	font-size: 0.84rem;
	line-height: 1.4;
	color: var(--muted);
}

.destination-modal__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	margin-bottom: 0.5rem;
}

.destination-modal__progress {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 1rem;
	padding: 0.75rem 0.9rem;
	border: 1px solid var(--border);
	border-radius: 6px;
	background: #faf8f4;
	margin-bottom: 0.75rem;
}

.destination-modal__progress h4 {
	margin: 0.15rem 0 0.2rem;
	font-size: 1rem;
}

.destination-modal__summary {
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-wrap: wrap;
	gap: 0.5rem 0.9rem;
	padding: 0.5rem 0.7rem;
	border: 1px solid var(--border);
	border-radius: 4px;
	background: #fbfbfa;
	margin-bottom: 0.8rem;
}

.destination-modal__body {
	display: grid;
	gap: 0.75rem;
}

.destination-stage {
	display: grid;
	gap: 0.85rem;
}

.destination-stage__note {
	margin: 0;
}

.destination-card {
	border: 1px solid var(--border);
	border-radius: 4px;
	padding: 0.75rem;
	background: #fff;
}

.destination-card__header {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 1rem;
	margin-bottom: 0.6rem;
}

.inline-number,
.inline-input {
	width: 100%;
	border: 1px solid var(--border);
	border-radius: 4px;
	height: 32px;
	padding: 0 0.5rem;
	background: #fff;
	font-size: 0.84rem;
	color: var(--text);
}

.inline-number {
	min-width: 110px;
}

.destination-select {
	height: 40px;
	padding: 0 0.75rem;
	border-radius: 4px;
	border: 1px solid var(--border);
	background: #fff;
}

.destination-form-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 0.9rem 1rem;
}

.destination-field {
	display: grid;
	gap: 0.35rem;
	font-size: 0.82rem;
	font-weight: 600;
	color: var(--text);
}

.destination-field--full {
	grid-column: 1 / -1;
}

.destination-field--checkbox {
	display: grid;
	grid-template-columns: auto 1fr;
	align-items: center;
	gap: 0.75rem;
	padding: 0.75rem 0.85rem;
	border: 1px solid var(--border);
	border-radius: 6px;
	background: #fcfbf8;
}

.destination-field--checkbox span,
.destination-field--checkbox small {
	display: block;
}

.destination-field--checkbox small {
	margin-top: 0.18rem;
	font-size: 0.75rem;
	font-weight: 400;
}

.destination-investment {
	display: grid;
	gap: 0.7rem;
}

.destination-holdings__header h5 {
	margin: 0;
	font-size: 1rem;
}

.holding-card__metric {
	display: grid;
	gap: 0.18rem;
	padding: 0.7rem 0.75rem;
	border: 1px solid var(--border);
	border-radius: 4px;
	background: rgba(255, 255, 255, 0.78);
}

.holding-card__metric span {
	font-size: 0.72rem;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--muted);
}

.holding-card__metric strong {
	font-family: var(--font-mono);
	font-size: 0.95rem;
}

.destination-investment__meta {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: 0.75rem;
	align-items: end;
	padding: 0.85rem 1rem;
	border: 1px solid var(--border);
	border-radius: 6px;
	background: #fcfbf8;
}

.destination-investment__cash {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	padding: 0.85rem 1rem;
	border: 1px solid var(--border);
	border-radius: 6px;
	background: #fcfbf8;
}

.destination-holdings {
	display: grid;
	gap: 0.75rem;
	padding: 0.9rem 1rem;
	border: 1px solid var(--border);
	border-radius: 6px;
	background: #faf8f4;
}

.destination-holdings__header {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 1rem;
}

.destination-holdings__stats {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 0.65rem;
}

.destination-holdings__empty {
	padding: 1rem;
	border: 1px dashed var(--border);
	border-radius: 4px;
	background: rgba(255, 255, 255, 0.75);
}

.holding-card {
	display: grid;
	gap: 0.8rem;
	padding: 0.9rem;
	border: 1px solid #ddd4c8;
	border-radius: 6px;
	background: #fff;
}

.holding-card__header {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 1rem;
}

.holding-card__header p {
	margin: 0.18rem 0 0;
}

.holding-card__grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 0.75rem;
}

.holding-card__grid label {
	display: grid;
	gap: 0.3rem;
	font-size: 0.82rem;
	font-weight: 600;
	color: var(--text);
}

.holding-card__metric {
	align-content: start;
}

.destination-investment__footer {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 0.75rem;
}

.destination-investment__actions {
	display: flex;
	gap: 0.5rem;
}

.destination-review-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 0.75rem;
}

.destination-review-item {
	display: grid;
	gap: 0.2rem;
	padding: 0.7rem 0.8rem;
	border: 1px solid var(--border);
	border-radius: 6px;
	background: #faf8f4;
}

.destination-review-item span {
	font-size: 0.72rem;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--muted);
}

.destination-review-holdings {
	display: grid;
	gap: 0.5rem;
}

.destination-review-holding {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto auto;
	gap: 0.75rem;
	padding: 0.65rem 0.75rem;
	border: 1px solid var(--border);
	border-radius: 6px;
	background: #fff;
}

.destination-modal__footer {
	display: flex;
	justify-content: flex-end;
	gap: 0.6rem;
	margin-top: 0.9rem;
}

.destination-modal--type .destination-modal__footer {
	justify-content: space-between;
}

.preview-validation-card {
	padding: 1rem;
}

.preview-validation-card__row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	margin-bottom: 0.45rem;
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

.success-cta {
	width: 100%;
	max-width: 360px;
	background: var(--text);
	border-color: var(--text);
	color: var(--bg);
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

	.migration-header__actions,
	.destination-modal__header,
	.destination-modal__progress,
	.destination-investment__meta,
	.destination-investment__cash,
	.destination-holdings__header,
	.holding-card__header,
	.destination-investment__footer,
	.destination-investment__actions {
		flex-direction: column;
		align-items: flex-start;
	}

	.destination-type-grid {
		grid-template-columns: 1fr;
	}

	.destination-investment__meta {
		grid-template-columns: 1fr;
	}

	.destination-holdings__stats,
	.destination-form-grid,
	.destination-review-grid,
	.holding-card__grid {
		grid-template-columns: 1fr;
	}

	.destination-review-holding {
		grid-template-columns: 1fr;
	}

	.transfer-action-bar {
		width: 100%;
		border-radius: 10px;
	}
}
</style>
