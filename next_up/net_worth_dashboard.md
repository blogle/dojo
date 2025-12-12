# Functional Specification: Net Worth Dashboard

## 1. Overview
The Dashboard serves as the application's landing page (`/`), providing an immediate, high-level view of the user's financial health. The design prioritizes a rich, interactive data visualization of Net Worth history, supported by summary widgets for account balances and key budget categories.

## 2. Layout & Structure
* **Global Navigation:** The standard Dojo application header remains visible at the top.
* **Page Container:**
    * **Header Section:** Left-aligned Net Worth summary.
    * **Hero Chart:** A full-bleed (edge-to-edge) interactive area chart spanning the entire viewport width.
    * **Controls:** Left-aligned time interval toggles immediately following the chart.
    * **Widget Grid:** A responsive grid (1 column on mobile, split 3:2 on desktop) containing the Accounts panel and Budget Watchlist.

## 3. Component Specifications

### 3.1. Net Worth Header
* **Position:** Top of the page content, left-aligned.
* **Elements:**
    * Label: "NET WORTH" (uppercase, muted).
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

### 3.4. Accounts Panel
* **Purpose:** A summary list of all active financial accounts.
* **Data:**
    * Account Name.
    * Account Type (Cash, Investment, Credit, etc.).
    * Current Balance (Currency formatted).
    * Recent Performance (% change over selected interval).
* **Sorting:** Sorted by current balance (descending).

### 3.5. Budget Watchlist
* **Purpose:** Quick-glance status of high-priority budget categories (e.g., Groceries, Dining).
* **Visuals:** Sparkline (progress bar) style.
* **Data Display:**
    * **Header:** Category Name.
    * **Bar:** Visualizes `(Available / Allocated) * 100`.
    * **Footer:** Left-aligned text reading: `[Available Amount] of [Allocated Amount] budgeted`.
* **States:**
    * **Normal:** Bar fills based on percentage.
    * **Empty/Overspent:**
        * Bar fill is transparent.
        * Bar outline is Red (`var(--danger)`).
        * Footer text turns Red and displays a Warning Icon with text "Unfunded / Overspent".

## 4. Technical Requirements (Frontend)
* **API:**
    * Requires a new endpoint: `GET /api/net-worth/history?interval={interval}`.
    * Response format: Array of `{ date: ISOString, value: Integer (minor units) }`.
* **Responsiveness:**
    * Chart must resize gracefully on window resize.
    * Tooltip positioning must account for screen edges (flipping anchor from left to right) to prevent overflow.
* **Performance:**
    * Chart interactions (hover/drag) must run at 60fps.
    * Use `requestAnimationFrame` or efficient reactive refs for cursor tracking.


# Single page Mockup
```
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dojo Dashboard Mockup</title>
    <script type="importmap">
      {
        "imports": {
          "vue": "https://unpkg.com/vue@3/dist/vue.esm-browser.js"
        }
      }
    </script>
    <style>
        /* --- Base Styles (from base.css) --- */
        :root {
            --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: "JetBrains Mono", "Fira Code", "IBM Plex Mono", ui-monospace, monospace;
            --bg: #fdfcfb;
            --surface: #ffffff;
            --text: #333333;
            --muted: #8a8a8a;
            --border: #e0e0e0;
            --primary: #5a6e5a;
            --primary-hover: #4a5c4a;
            --accent: #c7b299;
            --danger: #9c4843;
            --success: #6b8e23;
            --stone-50: #fafaf9;
            --shadow-hard: 4px 4px 0px 0px rgba(0, 0, 0, 0.75);
            --border-thick: 2px solid var(--text);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: var(--font-sans);
            background-color: var(--bg);
            color: var(--text);
            padding: 0; /* Reset body padding for full-width header */
            overflow-x: hidden; /* Prevent scrollbar from full-width elements */
        }
        
        /* Layout Wrapper */
        .app-shell {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem;
        }

        /* --- Header (from layout.css) --- */
        .app-header {
            display: flex;
            align-items: center;
            padding: 1.5rem 0;
            border-bottom: var(--border-thick);
            margin-bottom: 2rem;
        }

        .app-header__logo {
            font-family: var(--font-mono);
            font-weight: 700;
            font-size: 1.5rem;
            text-decoration: none;
            color: var(--text);
        }

        .app-header__nav {
            margin-left: auto;
            display: flex;
            gap: 1.5rem;
        }

        .app-header__link {
            font-family: var(--font-mono);
            font-size: 1rem;
            font-weight: 500;
            color: var(--muted);
            transition: color 0.2s ease-in-out;
            text-decoration: none;
        }

        .app-header__link:hover,
        .app-header__link--active {
            color: var(--text);
        }

        /* --- Global Buttons --- */
        .button {
            cursor: pointer;
            border: var(--border-thick);
            border-radius: 0;
            padding: 0.5rem 1rem;
            font-weight: 700;
            background: transparent;
            font-family: var(--font-sans);
            font-size: 0.9rem;
        }
        
        .button--tertiary { border: none; padding: 0.25rem 0.5rem; text-decoration: underline; }

        /* --- Dashboard Specific Styles --- */
        .dashboard-page {
            width: 100%;
            padding-bottom: 4rem;
        }

        .dashboard-page__header {
            display: flex;
            flex-direction: column;
            align-items: flex-start; /* Left Align */
            margin-bottom: 1rem; /* Reduced bottom margin since chart handles spacing */
            text-align: left; /* Left Align */
        }

        .net-worth-display {
            display: flex;
            flex-direction: column;
            align-items: flex-start; /* Left Align */
            gap: 0.5rem;
        }

        .net-worth-display__label {
            font-family: var(--font-mono);
            color: var(--muted);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .net-worth-display__value {
            font-size: 3rem;
            font-weight: 700;
            line-height: 1;
            color: var(--text);
            font-variant-numeric: tabular-nums;
        }

        .net-worth-display__change {
            font-family: var(--font-mono);
            font-size: 1rem;
            font-weight: 500;
            font-variant-numeric: tabular-nums;
        }

        .net-worth-display__change--positive { color: var(--success); }
        .net-worth-display__change--negative { color: var(--danger); }

        /* Chart */
        .chart-container {
            position: relative;
            /* Full Bleed Logic */
            width: 100vw;
            margin-left: 50%;
            transform: translateX(-50%);
            
            height: 400px; /* Slightly taller */
            margin-bottom: 2rem;
            overflow: hidden; 
            cursor: crosshair;
            user-select: none;
            -webkit-user-select: none;
            border-bottom: 1px solid var(--border); /* Subtle delimiter */
        }

        .chart-svg {
            width: 100%;
            height: 100%;
            display: block;
        }

        .chart-line {
            fill: none;
            stroke-width: 2.5;
            stroke-linecap: round;
            stroke-linejoin: round;
            vector-effect: non-scaling-stroke;
            transition: stroke 0.2s ease;
        }

        .chart-area {
            opacity: 0.6; /* Higher base opacity for gradient control */
            transition: fill 0.2s ease;
        }

        .chart-cursor-line {
            stroke: var(--muted);
            stroke-width: 1;
            stroke-dasharray: 4;
        }

        .chart-drag-line {
            stroke: var(--text);
            stroke-width: 1;
            opacity: 0.5;
            stroke-dasharray: 0;
        }

        .chart-drag-area {
            fill: var(--text);
            opacity: 0.03;
        }

        .chart-tooltip {
            position: absolute;
            top: 20px;
            /* Dynamic left positioning via JS style */
            background: var(--surface);
            border: var(--border-thick);
            padding: 0.75rem 1rem;
            pointer-events: none;
            z-index: 10;
            box-shadow: var(--shadow-hard);
            border-radius: 0;
            min-width: 180px;
        }

        .chart-tooltip__range {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--muted);
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            display: block;
        }

        .chart-tooltip__values {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
            margin-bottom: 0.5rem;
        }

        .chart-tooltip__row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            font-size: 0.9rem;
        }
        
        .chart-tooltip__row--main {
            font-weight: 700;
            font-size: 1.1rem;
        }

        .chart-tooltip__label {
            color: var(--muted);
            font-size: 0.8rem;
        }

        .chart-tooltip__stats {
            border-top: 1px solid var(--border);
            padding-top: 0.5rem;
            font-family: var(--font-mono);
            font-size: 0.85rem;
            display: flex;
            gap: 0.5rem;
        }

        /* Controls */
        .chart-controls {
            display: flex;
            justify-content: flex-start; /* Left align controls to match header */
            gap: 0.5rem;
            margin-bottom: 3rem;
            flex-wrap: wrap;
        }

        .chart-interval-btn {
            background: none;
            border: 1px solid transparent;
            font-family: var(--font-mono);
            font-size: 0.85rem;
            padding: 0.35rem 0.75rem;
            cursor: pointer;
            color: var(--muted);
            border-radius: 4px;
            transition: all 0.2s ease;
        }

        .chart-interval-btn:hover {
            color: var(--text);
            background-color: var(--stone-50);
            border-color: var(--border);
        }

        .chart-interval-btn--active {
            background-color: var(--text);
            color: var(--bg);
        }

        .chart-interval-btn--active:hover {
            background-color: var(--text);
            color: var(--bg);
            border-color: var(--text);
        }

        /* Dashboard Grid */
        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }

        @media (min-width: 900px) {
            .dashboard-grid {
                grid-template-columns: 3fr 2fr;
            }
        }

        .dashboard-panel {
            background: var(--surface);
            border: var(--border-thick);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            height: fit-content;
        }

        .dashboard-panel__header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.75rem;
        }

        .dashboard-panel__title {
            font-family: var(--font-mono);
            font-size: 1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Account List */
        .account-list {
            display: flex;
            flex-direction: column;
        }

        .account-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.85rem 0;
            border-bottom: 1px solid var(--border);
            transition: background-color 0.2s;
        }
        
        .account-row:hover {
            background-color: var(--stone-50);
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            margin-left: -0.5rem;
            margin-right: -0.5rem;
        }

        .account-row:last-child {
            border-bottom: none;
        }

        .account-row__info {
            display: flex;
            flex-direction: column;
            gap: 0.1rem;
        }

        .account-row__name {
            font-weight: 600;
            font-size: 1rem;
        }

        .account-row__meta {
            font-size: 0.8rem;
            color: var(--muted);
            text-transform: uppercase;
            font-family: var(--font-mono);
        }

        .account-row__stats {
            text-align: right;
        }

        .account-row__balance {
            font-family: var(--font-mono);
            font-weight: 600;
            display: block;
            font-size: 1.1rem;
        }

        .account-row__change {
            font-size: 0.85rem;
            font-family: var(--font-mono);
        }

        .text-success { color: var(--success); }
        .text-danger { color: var(--danger); }
        .text-muted { color: var(--muted); }

        /* Budget Sparklines */
        .budget-spark-list {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .budget-spark-item {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .budget-spark-item__header {
            display: flex;
            justify-content: space-between;
            font-size: 0.95rem;
            font-weight: 600;
        }

        .budget-spark-item__track {
            height: 10px;
            background-color: var(--stone-50);
            border: 1px solid var(--border);
            border-radius: 6px;
            overflow: hidden;
            position: relative;
        }

        .budget-spark-item__fill {
            height: 100%;
            background-color: var(--primary);
            border-radius: 4px;
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .budget-spark-item__remaining {
            font-family: var(--font-mono);
            font-size: 0.8rem;
            color: var(--muted);
            display: flex;
            justify-content: flex-start;
        }

        .budget-spark-item--empty .budget-spark-item__track {
            border-color: var(--danger);
            background-color: #fff5f5;
        }

        .budget-spark-item--empty .budget-spark-item__remaining {
            color: var(--danger);
            justify-content: flex-start;
        }

        .warning-label {
            display: flex;
            align-items: center;
            gap: 0.35rem;
            font-weight: 600;
        }

        .warning-icon {
            width: 14px;
            height: 14px;
            stroke: currentColor;
            stroke-width: 2;
            fill: none;
        }
        
        .u-muted { color: var(--muted); font-size: 0.9rem; }
        .u-small-note { font-size: 0.8rem; }
    </style>
</head>
<body>

<div id="app" class="app-shell">
    
    <!-- Navigation (From App.vue context) -->
    <header class="app-header">
        <a href="#" class="app-header__logo">DOJO</a>
        <nav class="app-header__nav" aria-label="Primary">
          <a href="#" class="app-header__link app-header__link--active">Dashboard</a>
          <a href="#" class="app-header__link">Transactions</a>
          <a href="#" class="app-header__link">Transfers</a>
          <a href="#" class="app-header__link">Allocations</a>
          <a href="#" class="app-header__link">Assets &amp; Liabilities</a>
          <a href="#" class="app-header__link">Budgets</a>
        </nav>
    </header>

    <main class="dashboard-page">
        <!-- Header & Chart Stats (Static based on Interval) -->
        <header class="dashboard-page__header">
            <div class="net-worth-display">
                <span class="net-worth-display__label">Net Worth</span>
                <span class="net-worth-display__value">{{ headerDisplayValue }}</span>
                <span 
                    class="net-worth-display__change" 
                    :class="headerIsPositive ? 'net-worth-display__change--positive' : 'net-worth-display__change--negative'"
                >
                    {{ headerChangeValue }} ({{ headerChangePercent }})
                </span>
            </div>
        </header>

        <!-- Main Chart -->
        <div 
            class="chart-container" 
            ref="chartRef"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseLeave"
        >
            <svg class="chart-svg" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none">
                <defs>
                    <linearGradient id="chartGradientPositive" x1="0" x2="0" y1="0" y2="1">
                        <!-- Lower coefficient: higher opacity at top, slower fade -->
                        <stop offset="0%" stop-color="var(--success)" stop-opacity="0.4"/>
                        <stop offset="70%" stop-color="var(--success)" stop-opacity="0.1"/>
                        <stop offset="100%" stop-color="var(--bg)" stop-opacity="0" />
                    </linearGradient>
                    <linearGradient id="chartGradientNegative" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stop-color="var(--danger)" stop-opacity="0.4"/>
                        <stop offset="70%" stop-color="var(--danger)" stop-opacity="0.1"/>
                        <stop offset="100%" stop-color="var(--bg)" stop-opacity="0" />
                    </linearGradient>
                </defs>
                
                <!-- Area Fill -->
                <path 
                    :d="areaPath" 
                    class="chart-area" 
                    :style="{ fill: `url(#${chartStateIsPositive ? 'chartGradientPositive' : 'chartGradientNegative'})` }" 
                />
                
                <!-- Line Stroke -->
                <path 
                    :d="linePath" 
                    class="chart-line" 
                    :style="{ stroke: chartStateIsPositive ? 'var(--success)' : 'var(--danger)' }" 
                />
                
                <!-- Drag Start Indicator -->
                <line 
                    v-if="dragStartData" 
                    :x1="dragStartData.x" 
                    y1="0" 
                    :x2="dragStartData.x" 
                    :y2="height" 
                    class="chart-drag-line" 
                />

                <!-- Selection Rectangle -->
                <rect 
                    v-if="dragStartData && hoverData"
                    :x="Math.min(dragStartData.x, hoverX)"
                    y="0"
                    :width="Math.abs(hoverX - dragStartData.x)"
                    :height="height"
                    class="chart-drag-area"
                />

                <!-- Current Hover Indicator -->
                <line 
                    v-if="hoverData" 
                    :x1="hoverX" 
                    y1="0" 
                    :x2="hoverX" 
                    :y2="height" 
                    class="chart-cursor-line" 
                />
                <circle 
                    v-if="hoverData" 
                    :cx="hoverX" 
                    :cy="hoverY" 
                    r="6" 
                    fill="var(--surface)" 
                    :stroke="chartStateIsPositive ? 'var(--success)' : 'var(--danger)'" 
                    stroke-width="3" 
                />
            </svg>
            
            <!-- Tooltip -->
            <div 
                v-if="hoverData" 
                class="chart-tooltip"
                :style="tooltipStyle"
            >
                <!-- DRAG STATE: Detailed stats -->
                <template v-if="dragStartData">
                    <span class="chart-tooltip__range">
                        {{ formatDateShort(startDateForTooltip) }} – {{ formatDateShort(hoverData.date) }}
                    </span>
                    <div class="chart-tooltip__values">
                        <div class="chart-tooltip__row">
                            <span class="chart-tooltip__label">Start</span>
                            <span>{{ formatAmount(startValueForTooltip) }}</span>
                        </div>
                        <div class="chart-tooltip__row">
                            <span class="chart-tooltip__label">End</span>
                            <span>{{ formatAmount(hoverData.value) }}</span>
                        </div>
                    </div>
                    <div class="chart-tooltip__stats" :class="tooltipChange >= 0 ? 'text-success' : 'text-danger'">
                        <strong>{{ tooltipChange >= 0 ? '+' : '' }}{{ formatAmount(tooltipChange) }}</strong>
                        <span>({{ tooltipPercent }}%)</span>
                    </div>
                </template>

                <!-- HOVER STATE: Simple stats -->
                <template v-else>
                    <span class="chart-tooltip__date">{{ formatDate(hoverData.date) }}</span>
                    <span class="chart-tooltip__value">{{ formatAmount(hoverData.value) }}</span>
                </template>
            </div>
        </div>

        <nav class="chart-controls">
            <button 
                v-for="interval in intervals" 
                :key="interval"
                type="button" 
                class="chart-interval-btn"
                :class="{ 'chart-interval-btn--active': selectedInterval === interval }"
                @click="changeInterval(interval)"
            >
                {{ interval }}
            </button>
        </nav>

        <!-- Widgets -->
        <div class="dashboard-grid">
            
            <!-- Accounts Panel -->
            <article class="dashboard-panel">
                <header class="dashboard-panel__header">
                    <h2 class="dashboard-panel__title">Accounts</h2>
                    <span class="u-muted u-small-note">Real-time balances</span>
                </header>
                <div class="account-list">
                    <div v-for="acct in accounts" :key="acct.id" class="account-row">
                        <div class="account-row__info">
                            <span class="account-row__name">{{ acct.name }}</span>
                            <span class="account-row__meta">{{ acct.type }}</span>
                        </div>
                        <div class="account-row__stats">
                            <span class="account-row__balance">{{ formatAmount(acct.balance) }}</span>
                            <span class="account-row__change" :class="acct.change >= 0 ? 'text-success' : 'text-danger'">
                                {{ acct.change >= 0 ? '+' : '' }}{{ acct.change }}%
                            </span>
                        </div>
                    </div>
                </div>
            </article>

            <!-- Budgets Panel -->
            <article class="dashboard-panel">
                <header class="dashboard-panel__header">
                    <h2 class="dashboard-panel__title">Budget Watchlist</h2>
                    <button class="button button--tertiary">Edit List</button>
                </header>
                <div class="budget-spark-list">
                    <div 
                        v-for="budget in budgets" 
                        :key="budget.id" 
                        class="budget-spark-item"
                        :class="{ 'budget-spark-item--empty': isBudgetEmpty(budget) }"
                    >
                        <div class="budget-spark-item__header">
                            <span>{{ budget.name }}</span>
                        </div>
                        <div class="budget-spark-item__track">
                            <div 
                                class="budget-spark-item__fill" 
                                :style="{ width: calculateProgress(budget) + '%', backgroundColor: isBudgetEmpty(budget) ? 'transparent' : '' }"
                            ></div>
                        </div>
                        <div class="budget-spark-item__remaining">
                            <span v-if="isBudgetEmpty(budget)" class="warning-label">
                                <svg class="warning-icon" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                                Unfunded / Overspent
                            </span>
                            <span v-else>
                                <strong style="color: var(--text)">{{ formatAmount(budget.available) }}</strong> &nbsp;of {{ formatAmount(budget.allocated) }} budgeted
                            </span>
                        </div>
                    </div>
                </div>
            </article>
        </div>
    </main>
</div>

<script type="module">
    import { createApp, ref, computed, onMounted } from 'vue';

    createApp({
        setup() {
            // --- Configuration ---
            const width = 1000;
            const height = 400; // Updated height
            const intervals = ["1D", "1W", "1M", "3M", "YTD", "1Y", "5Y", "Max"];
            const selectedInterval = ref("1M");
            
            const chartRef = ref(null);
            const hoverData = ref(null);
            const hoverX = ref(0);
            const hoverY = ref(0);

            // Drag State
            const isDragging = ref(false);
            const dragStartData = ref(null);

            // --- Mock Data Generators ---
            const generateHistory = (points, startValue, volatility) => {
                const data = [];
                let current = startValue;
                const now = new Date();
                
                for (let i = points; i >= 0; i--) {
                    const date = new Date(now);
                    date.setDate(date.getDate() - i);
                    const change = (Math.random() - 0.45) * volatility; 
                    current += change;
                    data.push({
                        date: date.toISOString().slice(0, 10),
                        value: Math.round(current)
                    });
                }
                return data;
            };

            const historyData = ref([]);

            const loadHistory = (interval) => {
                let points = 30;
                let volatility = 50000;
                const base = 15000000;
                switch(interval) {
                    case '1D': points = 24; volatility = 5000; break;
                    case '1W': points = 7; volatility = 20000; break;
                    case '1M': points = 30; volatility = 50000; break;
                    case '3M': points = 90; volatility = 80000; break;
                    case 'YTD': points = 180; volatility = 100000; break;
                    case '1Y': points = 365; volatility = 150000; break;
                    case '5Y': points = 60 * 5; volatility = 300000; break;
                    case 'Max': points = 500; volatility = 500000; break;
                }
                historyData.value = generateHistory(points, base, volatility);
            };

            const changeInterval = (interval) => {
                selectedInterval.value = interval;
                loadHistory(interval);
                isDragging.value = false;
                dragStartData.value = null;
            };

            // --- Chart Computations ---
            const dataPoints = computed(() => {
                const data = historyData.value;
                if (!data.length) return [];
                const values = data.map(d => d.value);
                const minVal = Math.min(...values);
                const maxVal = Math.max(...values);
                const range = maxVal - minVal || 1;
                const padding = range * 0.15; // Increased padding slightly

                return data.map((d, i) => ({
                    x: (i / (data.length - 1)) * width,
                    y: height - ((d.value - (minVal - padding)) / (range + padding * 2)) * height,
                    original: d
                }));
            });

            const linePath = computed(() => {
                const pts = dataPoints.value;
                if (!pts.length) return "";
                // Use standard simple lines for performance and crispness
                return pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
            });

            const areaPath = computed(() => {
                const line = linePath.value;
                if (!line) return "";
                return `${line} L ${width},${height} L 0,${height} Z`;
            });

            // --- Header Stats (Static per Interval) ---
            const headerDisplayValue = computed(() => {
                const data = historyData.value;
                if (!data.length) return "—";
                return formatAmount(data[data.length - 1].value);
            });

            const headerChangeValue = computed(() => {
                const data = historyData.value;
                if (data.length < 2) return "$0.00";
                const start = data[0].value;
                const end = data[data.length - 1].value;
                const diff = end - start;
                return (diff >= 0 ? "+" : "") + formatAmount(diff);
            });

            const headerChangePercent = computed(() => {
                const data = historyData.value;
                if (data.length < 2) return "0.00%";
                const start = data[0].value;
                const end = data[data.length - 1].value;
                if (start === 0) return "0.00%";
                const pct = ((end - start) / start) * 100;
                return pct.toFixed(2) + "%";
            });

            const headerIsPositive = computed(() => headerChangeValue.value.includes("+"));

            // --- Chart Dynamic Coloring State ---
            // If dragging, color based on drag selection. If not, color based on Interval trend.
            const chartStateIsPositive = computed(() => {
                if (dragStartData.value && hoverData.value) {
                    return (hoverData.value.value - dragStartData.value.value) >= 0;
                }
                return headerIsPositive.value;
            });

            // --- Tooltip Computations ---
            const startDateForTooltip = computed(() => dragStartData.value ? dragStartData.value.date : null);
            const startValueForTooltip = computed(() => dragStartData.value ? dragStartData.value.value : 0);
            
            const tooltipChange = computed(() => {
                if (!dragStartData.value || !hoverData.value) return 0;
                return hoverData.value.value - dragStartData.value.value;
            });

            const tooltipPercent = computed(() => {
                if (!dragStartData.value || !hoverData.value || dragStartData.value.value === 0) return "0.00";
                const pct = ((hoverData.value.value - dragStartData.value.value) / dragStartData.value.value) * 100;
                return pct.toFixed(2);
            });

            const tooltipStyle = computed(() => {
                // Ensure tooltip doesn't overflow screen
                const x = hoverX.value;
                const screenW = window.innerWidth;
                const chartW = width; // SVG coordinate
                // Approximate pixel position relative to screen center
                // Since chart is 100vw, hoverX/width is ratio
                let leftPct = (x / width) * 100; 
                
                // Flip anchor if too close to right edge
                if (leftPct > 85) {
                    return { left: x + 'px', transform: 'translateX(-100%)' };
                } else if (leftPct < 15) {
                    return { left: x + 'px', transform: 'translateX(0)' };
                }
                return { left: x + 'px', transform: 'translateX(-50%)' };
            });

            // --- Interaction Handlers ---
            const getPointFromEvent = (e) => {
                if (!chartRef.value || !dataPoints.value.length) return null;
                const rect = chartRef.value.getBoundingClientRect();
                const rawX = e.clientX - rect.left;
                if (rawX < 0 || rawX > rect.width) return null; // Out of bounds

                const scaledX = (rawX / rect.width) * width;
                const index = Math.round((scaledX / width) * (dataPoints.value.length - 1));
                return dataPoints.value[index];
            };

            const handleMouseDown = (e) => {
                const point = getPointFromEvent(e);
                if (point) {
                    isDragging.value = true;
                    // Store x/y/original for the start point
                    dragStartData.value = { ...point.original, x: point.x, y: point.y };
                    window.addEventListener('mouseup', handleGlobalMouseUp);
                }
            };

            const handleMouseMove = (e) => {
                const point = getPointFromEvent(e);
                if (point) {
                    hoverX.value = point.x;
                    hoverY.value = point.y;
                    hoverData.value = point.original;
                }
            };

            const handleMouseUp = () => {
                isDragging.value = false;
                dragStartData.value = null;
                window.removeEventListener('mouseup', handleGlobalMouseUp);
            };

            const handleMouseLeave = () => {
                if (!isDragging.value) {
                    hoverData.value = null;
                }
            };

            const handleGlobalMouseUp = () => {
                handleMouseUp();
            };

            // --- Formatters & Mock Data ---
            const formatAmount = (minor) => {
                return new Intl.NumberFormat("en-US", {
                    style: "currency",
                    currency: "USD",
                    minimumFractionDigits: 2
                }).format(minor / 100);
            };

            const formatDate = (isoStr) => {
                const d = new Date(isoStr);
                return d.toLocaleDateString(undefined, { 
                    month: 'short', 
                    day: 'numeric', 
                    year: 'numeric',
                    hour: selectedInterval.value === '1D' ? 'numeric' : undefined 
                });
            };

            const formatDateShort = (isoStr) => {
                if(!isoStr) return "";
                const d = new Date(isoStr);
                return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
            };

            const accounts = ref([
                { id: 1, name: "Main Checking", type: "Cash", balance: 1250045, change: 1.2 },
                { id: 2, name: "Vanguard Brokerage", type: "Investment", balance: 8450000, change: 0.8 },
                { id: 3, name: "Chase Sapphire", type: "Credit Card", balance: -45020, change: -5.4 },
                { id: 4, name: "High Yield Savings", type: "Accessible Asset", balance: 3000000, change: 0.05 },
            ]);

            const budgets = ref([
                { id: 'groc', name: "Groceries", allocated: 60000, available: 25050 },
                { id: 'dine', name: "Dining Out", allocated: 30000, available: 5000 },
                { id: 'gas', name: "Gas / Fuel", allocated: 15000, available: 12000 },
                { id: 'fun', name: "Fun Money", allocated: 20000, available: 0 },
                { id: 'rent', name: "Rent", allocated: 220000, available: 220000 },
                { id: 'oops', name: "Misc", allocated: 0, available: -5000 },
            ]);

            const isBudgetEmpty = (b) => b.allocated === 0 || b.available <= 0;
            const calculateProgress = (b) => {
                if (b.allocated === 0) return 0;
                const pct = (b.available / b.allocated) * 100;
                return Math.max(0, Math.min(100, pct));
            };

            onMounted(() => loadHistory("1M"));

            return {
                width, height, intervals, selectedInterval, changeInterval,
                chartRef, handleMouseDown, handleMouseMove, handleMouseUp, handleMouseLeave,
                hoverData, hoverX, hoverY, dragStartData,
                linePath, areaPath,
                headerDisplayValue, headerChangeValue, headerChangePercent, headerIsPositive,
                tooltipChange, tooltipPercent, startDateForTooltip, startValueForTooltip, tooltipStyle, chartStateIsPositive,
                accounts, budgets, formatAmount, formatDate, formatDateShort, isBudgetEmpty, calculateProgress
            };
        }
    }).mount('#app');
</script>

</body>
</html>
```
