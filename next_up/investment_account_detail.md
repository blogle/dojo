Page follows the existing style guidelines of dojo.
Dojo title and navigation bar

## 1. Overview
This page serves as the investment account detail page. It provides a place within the application to monitor the performance of a specific investment account within the application along with its holdings. The page is also the touch point for users to update their holdings within that respective account. This page is accessed through the assets and liabilities page by clicking into one of the previously added investment accounts.

## 2. Layout & Structure
* **Global Navigation:** The standard Dojo application header remains visible at the top.
* **Page Container:**
    * **Header Section:** Title matches the name of the selected account.
    * **Chart container**: below the title is a container that include a hero chart tracking the performance of this respective account.
    * **Hero Chart:** A full-bleed (edge-to-edge) interactive area chart spanning the entire container.
    * **Controls:** Left-aligned time interval toggles immediately following the chart.
    * **Details** To the right of the chart is another container including account details - NAV, Cost, Deposits, %of total portfolio, todays return $/%, total return $/%, account type: IRA, individual, 401k, etc
    ** Cash Balance** Beneath details is the current cash balance held within the account - this is the amount available for investments or to be transferred out of the cacount into a budget account.
    * **Holdings** Beneath the chart, details and cash balance containers is a table matching the implementation used in transactions and alloctations pages. This page displays all of the positions within the account

## 3. Component Specifications

### 3.1. Account Header
* **Position:** Top of the page content, left-aligned.
* **Elements:**
    * Label: "{Account name}" (uppercase, muted). eg "Robinhood Individual"
    * Current Value: Large typography, displays the most recent data point.
    * Change Metrics: Absolute currency change and percentage change.
* **Behavior:**
    * **Static Context:** These values reflect the change over the *entire currently selected time interval* (e.g., "This Month" or "YTD"). They do *not* update dynamically on hover/drag (unlike Robinhood); dynamic measurement is handled exclusively by the chart tooltip.
    * **Color Coding:**
        * Positive change: Green (`var(--success)`).
        * Negative change: Red (`var(--danger)`).

### 3.2. Interactive History Chart
* **Visual Style:**
    * **Type:** Area chart with a smooth stroke.
    * **Width:** Full viewport width (`100vw`), breaking out of the main page container margins.
    * **Coloring:**
        * The stroke and fill color are dynamic based on the trend of the *displayed data slice*.
        * If (End Value >= Start Value): Green.
        * If (End Value < Start Value): Red.
    * **Gradient:** The fill uses a linear gradient starting at ~40% opacity at the top, holding steady until 85% down, and fading to 0% opacity (background color) at the very bottom.
* **Interaction Model:**
    * **Default State:** Shows the trend for the selected interval.
    * **Hover State:**
        * Displays a vertical cursor line and a point on the graph.
        * Tooltip appears showing the specific Date and Value at the cursor.
    * **Drag-to-Measure State:**
        * **Trigger:** User clicks and holds (mousedown) on the chart.
        * **Visuals:**
            * A static vertical line marks the "Start" (click) point.
            * A semi-transparent rectangular overlay highlights the region between the Start point and current cursor.
            * The chart color (Green/Red) updates dynamically to reflect the performance of *only* the selected range.
        * **Tooltip:** The tooltip expands to display:
            * Date Range: `Start Date – End Date`.
            * Values: `Start Value` and `End Value`.
            * Delta: Absolute change and Percentage change for the selection.

### 3.3. Time Interval Controls
* **Options:** 1D, 1W, 1M, 3M, YTD, 1Y, 5Y, Max.
* **Behavior:** Clicking an option reloads the chart data.
* **Selection:** The active interval is highlighted with a solid background; inactive buttons use a ghost style.


### 4. Holdings
The holdings table contains the following columns. Ticker (this columnn name can be hidden), Qty, Avg cost basis, Market Value, Current price, todays return, total return. There should be a form above the table with these fields that allows us to append new entries to the table. We can click into respective rows of the table to edit them. This actually applies a soft update (appends a new row) this is the mechansim we utilize (SCD2) to track equity over time in addition to marking all positions to the current market value. 

### 5. Cash
The cash balance also needs to be an editable field for the same tracknig reasons.



The Dashboard serves as the application's landing page (`/`), providing an immediate, high-level view of the user's financial health. The design prioritizes a rich, interactive data visualization of Net Worth history, supported by summary widgets for account balances and key budget categories.
