# Aspire Customization and Offsets

Aspire is implemented as a spreadsheet, so users can customize:

- the order of tabs,
- the placement of input sections,
- visible UI layout,
- some configuration and lookup tables.

A robust migration cannot assume fixed cell coordinates.

## Named ranges as the stable contract

Named ranges provide a stable pointer to the important regions of the sheet even when users move things around.

From exporter evidence (see `docs/aspire/named-ranges.md`), named ranges cover the most migration-critical “tables”:

- Transactions ledger: `trx_*`
- Category allocation event log: `cts_*`
- Net worth snapshot log: `ntw_*`
- Accounts configuration: `cfg_Accounts`, `cfg_Cards`
- Category configuration: `r_ConfigurationData`
- Semantic constants: `v_*` (special category labels and marker symbols)

## What breaks if a named range is missing or wrong

- If `trx_*` ranges are missing: the importer cannot reliably locate the transaction ledger.
- If `cts_*` ranges are missing: the importer cannot locate allocation history.
- If `r_ConfigurationData` is missing: the importer cannot reconstruct category groups/categories and goal settings.
- If `v_AtoB` / `v_AccountTransfer` are missing: the importer cannot reliably recognize Ready-to-Assign or transfers.

Observed fragility:

- Some named ranges can be malformed (e.g. missing `sheetId` in the Sheets API response) or empty. The tooling must skip these safely and use fallback strategies.

## Fallback strategies (when named ranges are absent)

When named ranges are missing or have been renamed, robust extraction should fall back to “structural signatures”:

- Locate the `Transactions` table by scanning for the header row `DATE | OUTFLOW | INFLOW | CATEGORY | ACCOUNT | MEMO | STATUS` and then reading the column block beneath it.
- Locate the `Category Allocation` table by scanning for the header row `DATE | AMOUNT | FROM CATEGORY | TO CATEGORY`.
- Locate the `Net Worth Reports` input block by scanning for the header row `DATE | AMOUNT | NET WORTH CATEGORY | NOTES`.

These fallbacks are less reliable than named ranges and should be used only when the sheet’s named range “API” is missing.
