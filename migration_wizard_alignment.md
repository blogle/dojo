# Onboarding flow

## Step 1. Welcome to dojo
two cards:
- start fresh: clicking this terminates the onboarding flow and result in dojo instance with empty db. We might consider adding some initial tutorial cards that give the user a walkthrough of the app - highlighting buttons and linking to pages guiding them, prompting them to create budgets, assets/liabilities and then input transactions.

- migrate from aspire: This starts the migration wizard guiding the user through mapping their aspire budgets google sheet data into dojo.

This document is focused on the secondary flow of migrating data from aspire.


## General Wizard Look/feel
- A progress bar appears in the nav bar indicating the number of remaining steps in the flow. The mock up @aspire_onboarding_mockup.html includes a title/header and nav bar, these mocks are meant to represent the full screen view - do not duplicate the title/nav bar in the implementation. None of the regular nav bar navigation links appear during the onboarding flow - instead just the text "onboarding". This is to prevent the user from navigating away from the page until onboarding is completed.
- the bottom of the screen are persistent stepper buttons back/continue - on the final step continue button text transitions to "finish".
- on the right side of the wizard aligned with the step title text we display a text badge indicating validation/consistency logic - this should provide feedback to the user as to whether the current step is in a passing state or needs user intervention - the user can hover over this badge to get a help tool tip.
- each page can optionally provide subtitle text providing a brief explanation of the page.
- actions performed within the wizard are durable/resumable. If the user accidentally closes the page, navigates away, etc - they should be able to reopen the app and resume progress where they left off. This can be acheived through usage of local storage or backend persistence as needed (though we should strongly avoid commiting partial state to the db!).


## Step 2. Connect google
- Step title text: "Connect Google Drive"
- subtext indicating the permisions we need and what we are doing with it
- single "Connect google account" button - clicking this button iniates an oauth flow.

## Step 3: User sheet input
- Step title text: "Which sheet are we using?"
- single text entry field for the user to paste the link to their spreadsheet (we display greyed out mock link until user entry).

## Transition: spinner
Between step 3 and 4 - we display a progress spinner while we fetch the user sheet. beneath the spinner we show temporary text indicating how we are currently processing the data.

## Step 4: Extraction Overview
- Step title text: "We found your data"
- This page displays cards summarizing the different entities that we found in their spreadsheet: # accounts, # transactions, # net worth marks, months/years of history detected.

## Step 5: Budget accounts
- Step title text: "Budget accounts"
- We display a table with the columns: account name, type, status, settled balance, pending balance
type must be one of the on-budget account types. status is active | retired - statuses have a fill color active=green, retired=grey. settled balance is the sum of transactions on the ledger associated with that account that have been marked as cleared. pending balance is the same - but for transactions that have been marked as pending.

## Step 6: Budget envelopes
- Step title text: "Budget categories"
- This page displays two separate tables - active budgets and retired budgets.
- Active budgets: columns category, group, config, configured budget, available. These values (except config) come from the configuration and dashboard sheets of aspire.
category is the name of the budget, group is the name of the group we associate to this category to, config is frequency or date of payment, configured budget is the target/goal amount set in the configuration page of aspire indicating how much we intend to budget each month (not how much we have budgeted/contributed this month), available is the current amount remaining in the envelope.
- Available column: each item in the available column is bold/underlined. These are not clickable, but indicate that these items have a hover over tooltip. When hovering over one of these amounts, we display this months activity and budgeted funds for the budget category. activity is the amount we have spent this month categorized to this spend, while budgeted is the amount we have contributed to the envelope since the start of the month (ignoring amounts rolling over from the prior month).
- each row also includes an edit icon (its a pen/pencil icon) - Clicking this enables the user to edit the properties of the budget: name, group and budget configuration. Dojo supports two budget configurations: recurring and target date. Recurring budgets have an ammount due at a given frequency (weekly, monthly, quarterly, annually) while target date budgets are associated with payments coming due on a specified date. Dojo uses this information to compute a monthly budget goal for the user to meet upcoming spending. This modal should likely recycle the component that is already available in the budgets page of the app.
- Retired budgets: These are the budgets that are not actively used in the aspire sheet or explicitly marked as hidden. The mockup currently displays this table with the same colums as active budgets, but that is not exactly necessary. We should display the columns: category, configured budget and available - its important that the user validate that the available amount is zero - if there is a balance we need to provide UI (likely a button on the row) to insert an allocation zeroing out the retired budget. Alternatively - we could just display this table as advisory information at this step, and add a step to the post migration todo list to resolve these balances. This is possibly a cleaner approach as it reduces friction to onboarding and enables the user to address these piecemeal at their convenience. 
- System categories and cards - Note on this page we do not display the system categories like "available to budget", "starting balance", etc - these are ALWAYS mapped into their corresponding category in dojo. Similarly we do not list out the card categories from aspire - all cards in dojo are automatically given a corresponding budget category.

## Step 7: Transfer Exceptions
- Step title text: "Transfer exceptions"
- in dojo all account transfers share a concept id - which is not the case in aspire. To address this dojo implements matching logic to attempt to pair all transfer legs in the migrated data. Any orphan legs must be resolved during migration.
- We display a table of these orphan legs: these include the transaction ledger columns date, account, category, memo and amount - each row also includes a check mark field. The mockup currently includes a "Resolution field" however this is unnecessary - instead clicking a row should make it editable as it does on the transaction ledger. This should enable the user to modify the transaction entry to categorized expense or system category like "balance adjustment" as to "unorphan" the row. Alternatively the user can select the checkbox of any two transaction legs, upon doing so a dialog appears with the text "2 transactions selected" and a clickable button "link as transfer". Once all orphaned transfers are resolved the user can proceed to the next step.
- The mockup currently hides rows that have been addressed, however this makes it difficult for users to correct mistakes or change their resolution. Instead we should likely just change the row color or add an indicator icon to rows that have been resolved, enabling users to re-edit their changes.

## Step 8: Consolidate net worth
- Step title text: Consolidate net worth
- note: I dont really like the name of this page, I feel its not descriptive of whats going on...
- Aspire requires dual reporting of accounts through different lenses - budgetting and net worth. accounts do not derive their value from transactions on the ledger, instead users must add networth marks to the net worth sheet in addition to inputting transactions for said account. Dojo instead derives the value of budget accounts from the ledger itself - during this step of the wizard we ask the user to pair these entities as to prevent double counting of these assets going forward in dojo. 
- Table with columns budget account, net worth account and strategy. Dojo uses a heuristic to find the matching net worth account for each budget account. This should be editable to allow the user to override the mappings and strategy. The merge of these accounts, indicates that going forward dojo will use the transactions on the ledger associtated with the budget account INSTEAD of the net worth account marks when computing net worth.

## Step 9: Migrate net worth
- Step title text: Net worth accounts
- For any net worth accounts that were not merged with a budget account in the prior step, we now ask the user to create new destination accounts that we will cutover to upon completion of the migration. This is to enable more granular tracking of assets and liablities in dojo with rich metadata as opposed to the periodic marks used in aspire. For example the user might have had a consolidated "retirement accounts" entry in aspire that now needs to be broken out into the constituent brokerage accounts in dojo, each with their own investment positions, cash balances, tax treatment, etc.
- We display a banner with the following fields "last reported net worth", "derived net worth" and "difference".
 - last reported net worth: this is currently displayed as "total legacy" in the mockup and is the total net worth derived from aspire marks as of migration.
 - derived net worth: this is the dojo derived net worth across all accounts (including budget accounts derived from the ledger)
 - difference: is the delta between these two values - the idea being that as the user wants to minimize the delta as they onboard each cutover account. We highly recommend that users input final net worth marks on aspire before migration. if there was any significant period of time between their net worth marks and the cutover date these values will not match - especially if they have brokerage accounts that are marked to market daily.
- We display an accordion like view for every net worth account in aspire (that wasn't previously linked to a budget account), the header of that accordian displays the name of the net worth account in aspire - its balance and a badge indicating if its matched (delta is within tolerance). Within the accordion is a "+ Add Destination account" button. When clicked this opens the create account wizard from the asset and liabilities page, allowing the user to onboard a new destination account for these funds. Once the account is added its displayed as a card in the accordian with a checkmark, account name, type and current value. The add destination account button remains beneath the cards, enabling the user to onboard multiple destination accounts for that net worth account. If there is a significant different between the cutover accounts and the net worth mark - we display a warning badge indicating "unbalanced".
- Upon completion of the wizard, we will use the sum balance of each respective cutover account to enter a final net worth mark for the migrated account - we will then produce offseting ledger transactions from the networth account into the destination accounts to provide their initial balances as required for performance reporting, etc. 

## Step 10: Preview Migration
- Step title text: Preview Migration
- This page displays a chart displaying the historical net worth value and the dojo derived net worth value - assuming all previous steps where completed/addressed there will be deviation, but it should be somewhat minimal. 
- The "continue" stepper button is now displayed as "Finish", clicking this button initiates the applying the migration

## Transition spinner
We display a page with a spinner with transitional summary text beneath that updates as we apply the migration to the database - providing feedback to the user of what is going on beneath the hood. This should be informative and not debug data - we should not display system logs, errors, etc here.

## Step 11: Confirmation page
- This is the final page of the wizard! This displays the text "Migration Complete!" and a button that links to the dashboard with text "Go to the Dashboard". Upon clicking this link we can now disable the onboarding flow in the application and direct the user to the dashboard. The dashboard should be updated to include a todo section containing high priority tasks that should be completed (for example zeroing out hidden budgets).
