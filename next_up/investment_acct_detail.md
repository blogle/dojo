# Specification: Investment Account Detail Page

## 1. Overview
The Investment Account Detail page provides a comprehensive view of a specific investment account's performance, asset allocation, and transaction history. It serves as the primary interface for monitoring Net Asset Value (NAV) growth and managing individual holdings (positions).

## 2. Visual Style & Layout
* **Theme:** Minimalist Earth Tones.
    * **Background:** `#fdfcfb` (Off-white).
    * **Surface:** `#ffffff` (White) with borders `#e0e0e0`.
    * **Typography:** Sans-serif (`Inter`) for UI text; Monospace (`JetBrains Mono`) for financial data and headers.
    * **Status Colors:** Success (`#6b8e23` - Green) and Danger (`#9c4843` - Red) used for performance metrics.
* **Grid Layout:**
    * **Desktop:** Two-column layout. Main content (Chart) takes remaining width (`1fr`); Sidebar takes fixed width (`320px`).
    * **Mobile:** Single-column stacked layout.

## 3. Component Breakdown

### 3.1 Global Navigation
* **Location:** Top of viewport.
* **Items:** Logo (DOJO), Transactions, Transfers, Allocations, Assets & Liabilities (Active), Budgets.
* **Style:** Simple text links; active state uses primary text color.

### 3.2 Page Header
* **Account Name:** Uppercase, muted, monospace font (e.g., "ROBINHOOD INDIVIDUAL").
* **Current Value:** Large, bold typography displaying the total account value (NAV).
* **Performance:** Displays absolute change (`$`) and percentage change (`%`) for the selected time period.
    * **Color Logic:** Green if positive, Red if negative.

### 3.3 Interactive Hero Chart
A responsive SVG-based area chart visualizing account value over time.

* **Visual Construction:**
    * **Line Path:** A solid stroke representing the value trend.
    * **Area Path:** A filled path beneath the line, using a linear gradient (Opacity: 40% top -> 10% mid -> 0% bottom).
    * **Coloring:** Dynamic based on trend. If `End Value >= Start Value`, the theme is Green; otherwise, Red.
* **Interactions:**
    * **Hover:** Displays a vertical cursor line, a data point dot, and a tooltip containing the Date and Value.
    * **Drag-to-Measure:**
        * **Action:** Click and drag horizontally.
        * **Visual:** Renders a semi-transparent overlay rectangle covering the selected time range.
        * **Tooltip:** Updates to show the specific change (Delta $ and %) between the start and end of the drag selection.
        * **Dynamic Styling:** The chart color temporarily changes to reflect the performance of *only* the selected range (e.g., a green chart might turn red if measuring a drawdown period).
* **Time Interval Controls:**
    * **Options:** 1D, 1W, 1M (Default), 3M, YTD, 1Y, Max.
    * **Behavior:** Fetches/generates new data points and re-renders the chart. Active tab is highlighted with a solid background.

### 3.4 Sidebar Details
* **Details Card:**
    * Key-value pairs for: NAV, Cost Basis, Cash, Total Return, and Account Type.
    * Total Return value is color-coded based on performance.
* **Cash Balance Card:**
    * Input field displaying the uninvested cash amount.
    * Right-aligned, monospace, large font weight.
    * Intended for quick manual adjustments.

### 3.5 Holdings Section
* **Header:** Title ("Holdings") and a "Toggle" button (`+ Add Position` / `Cancel`).
* **Add Position Form:**
    * Hidden by default.
    * Fields: Ticker, Quantity, Avg Cost, Current Price.
    * Actions: Cancel, Save Position.
* **Holdings Table:**
    * **Columns:** Ticker, Qty, Price, Avg Cost, Market Value, Total Return.
    * **Styling:** Rows highlight on hover.
    * **Data Formatting:** Currency values are formatted; Total Return uses color coding (Green/Red).

## 4. Technical Behaviors
* **Chart Rendering:** The chart is split into two distinct SVG paths (Stroke vs. Fill) to prevent the gradient fill from clipping or overlapping the stroke line visually.
* **Responsiveness:** The SVG `viewBox` scales to fit the container width.E

# Single page mockup
```
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dojo - Investment Account Mockup</title>
    <style>
        /* --- BASE CSS (Variables & Reset) --- */
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
        body { font-family: var(--font-sans); background-color: var(--bg); color: var(--text); padding: 2rem; }

        /* --- BUTTONS & UTILS --- */
        .button {
            cursor: pointer;
            border: var(--border-thick);
            background: transparent;
            padding: 0.5rem 1rem;
            font-weight: 700;
            font-family: var(--font-sans);
            transition: transform 0.1s;
        }
        .button:active { transform: translate(1px, 1px); }
        .button--primary { background-color: var(--primary); color: white; border-color: var(--text); }
        .button--secondary { background-color: var(--surface); color: var(--text); }
        .u-muted { color: var(--muted); font-size: 0.85rem; }
        .u-small-note { display: block; margin-top: 0.25rem; }

        /* --- FORMS --- */
        input {
            font-family: var(--font-mono);
            padding: 0.5rem;
            border: var(--border-thick);
            width: 100%;
            font-size: 1rem;
        }
        .form-panel__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
        .form-panel__field { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.9rem; font-weight: 600; }
        .form-panel__actions { margin-top: 1rem; display: flex; justify-content: flex-end; }

        /* --- LEDGER TABLE --- */
        .ledger-card { border: var(--border-thick); background: var(--surface); width: 100%; overflow-x: auto; }
        .ledger-table { width: 100%; border-collapse: collapse; }
        .ledger-table th, .ledger-table td { padding: 1rem; text-align: left; border-bottom: var(--border-thick); }
        .ledger-table thead { background-color: var(--accent); }
        .ledger-table__amount { text-align: right; font-family: var(--font-mono); }
        .ledger-table tbody tr:hover td { background-color: #f5f5f5; cursor: pointer; }

        /* --- INVESTMENT SPECIFIC STYLES (From investments.css) --- */
        .investment-page { padding-bottom: 4rem; max-width: 1400px; margin: 0 auto; }
        .investment-header { margin-bottom: 2rem; }
        .investment-header__title { font-family: var(--font-mono); text-transform: uppercase; color: var(--muted); font-size: 0.9rem; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
        .investment-header__value { font-size: 2.5rem; font-weight: 700; line-height: 1.1; margin-bottom: 0.5rem; }
        .investment-header__change { font-family: var(--font-mono); font-size: 1rem; font-weight: 500; }
        .investment-header__change--positive { color: var(--success); }
        .investment-header__change--negative { color: var(--danger); }

        .investment-grid { display: grid; grid-template-columns: 1fr 320px; gap: 2rem; margin-bottom: 3rem; }
        @media (max-width: 1024px) { .investment-grid { grid-template-columns: 1fr; } }

        /* Chart */
        .chart-container { background: var(--surface); border: var(--border-thick); padding: 1.5rem; display: flex; flex-direction: column; position: relative; min-height: 400px; user-select: none; }
        .chart-wrapper { flex-grow: 1; width: 100%; position: relative; cursor: crosshair; overflow: hidden; }
        .chart-svg { width: 100%; height: 100%; display: block; }
        .chart-overlay-rect { fill: var(--text); opacity: 0.1; }
        
        .chart-tooltip { position: absolute; top: 0; left: 0; background: var(--surface); border: var(--border-thick); padding: 0.5rem 0.75rem; pointer-events: none; z-index: 10; box-shadow: var(--shadow-hard); font-family: var(--font-mono); font-size: 0.85rem; display: none; }
        .chart-tooltip.is-visible { display: block; }
        .chart-tooltip__label { color: var(--muted); font-size: 0.75rem; margin-bottom: 0.25rem; }
        .chart-tooltip__value { font-weight: 700; }

        .chart-controls { display: flex; gap: 0.5rem; margin-top: 1rem; border-top: 1px solid var(--border); padding-top: 1rem; }
        .chart-control-btn { background: none; border: 1px solid transparent; padding: 0.25rem 0.75rem; font-family: var(--font-mono); font-size: 0.85rem; color: var(--muted); cursor: pointer; border-radius: 4px; transition: all 0.2s; }
        .chart-control-btn:hover { color: var(--text); background: var(--stone-50); }
        .chart-control-btn.is-active { color: var(--bg); background: var(--text); font-weight: 600; }

        /* Sidebar */
        .investment-sidebar { display: flex; flex-direction: column; gap: 1.5rem; }
        .detail-card { background: var(--surface); border: var(--border-thick); padding: 1.5rem; }
        .detail-card h3 { font-family: var(--font-mono); font-size: 0.9rem; text-transform: uppercase; color: var(--muted); margin-bottom: 1rem; letter-spacing: 0.05em; }
        .detail-list { display: flex; flex-direction: column; gap: 0.75rem; }
        .detail-item { display: flex; justify-content: space-between; align-items: baseline; font-size: 0.95rem; }
        .detail-item__label { color: var(--muted); }
        .detail-item__value { font-weight: 600; font-family: var(--font-mono); }
        .detail-item__value--positive { color: var(--success); }
        .detail-item__value--negative { color: var(--danger); }
        .cash-balance-input { width: 100%; text-align: right; font-family: var(--font-mono); font-weight: 700; font-size: 1.25rem; padding: 0.5rem; border: var(--border-thick); }

        /* Holdings */
        .holdings-section { margin-top: 2rem; }
        .holdings-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .holdings-header h2 { font-size: 1.5rem; font-weight: 700; }
        .add-holding-form { background: var(--surface); border: var(--border-thick); padding: 1.5rem; margin-bottom: 1.5rem; display: none; }
        .add-holding-form.is-visible { display: block; }

        /* Navigation Mockup */
        .mock-nav { display: flex; gap: 2rem; padding-bottom: 2rem; margin-bottom: 2rem; border-bottom: var(--border-thick); }
        .mock-nav a { text-decoration: none; color: var(--muted); font-family: var(--font-mono); font-weight: 600; }
        .mock-nav a.active { color: var(--text); }
        .mock-nav .logo { font-weight: 800; color: var(--text); margin-right: auto; font-size: 1.2rem; }

    </style>
</head>
<body>

    <!-- Global Navigation Mock -->
    <nav class="mock-nav">
        <div class="logo">DOJO</div>
        <a href="#">Transactions</a>
        <a href="#">Transfers</a>
        <a href="#">Allocations</a>
        <a href="#" class="active">Assets & Liabilities</a>
        <a href="#">Budgets</a>
    </nav>

    <div class="investment-page">
        <!-- Header -->
        <header class="investment-header">
            <h1 class="investment-header__title">Robinhood Individual</h1>
            <div class="investment-header__value">$42,850.25</div>
            <div class="investment-header__change investment-header__change--positive">
                +$1,250.00 (+3.01%)
            </div>
        </header>

        <div class="investment-grid">
            <!-- Chart Section -->
            <main>
                <div class="chart-container" id="chart-container">
                    <div class="chart-wrapper" id="chart-wrapper">
                        <div class="chart-tooltip" id="chart-tooltip">
                            <div class="chart-tooltip__label" id="tooltip-label"></div>
                            <div class="chart-tooltip__value" id="tooltip-value"></div>
                        </div>
                        <svg class="chart-svg" preserveAspectRatio="none" viewBox="0 0 1000 400" id="main-chart-svg">
                            <defs>
                                <linearGradient id="chartGradient" x1="0" x2="0" y1="0" y2="1">
                                    <stop offset="0%" stop-color="var(--success)" stop-opacity="0.4" id="grad-start"/>
                                    <stop offset="85%" stop-color="var(--success)" stop-opacity="0.1" id="grad-mid"/>
                                    <stop offset="100%" stop-color="var(--bg)" stop-opacity="0"/>
                                </linearGradient>
                            </defs>
                            <!-- 
                                Split Chart into Area (fill only) and Line (stroke only)
                                This prevents the fill from "clipping" through the line if it was one closed path.
                            -->
                            <path id="chart-area" d="" fill="url(#chartGradient)" stroke="none" />
                            <path id="chart-path" d="" stroke="var(--success)" stroke-width="3" fill="none" vector-effect="non-scaling-stroke" />
                            
                            <!-- Selection Overlay -->
                            <rect id="selection-rect" x="0" y="0" width="0" height="400" class="chart-overlay-rect" style="display:none;" />
                            
                            <!-- Cursor Line -->
                            <g id="cursor-group" style="display:none;">
                                <line id="cursor-line" x1="0" y1="0" x2="0" y2="400" stroke="var(--text)" stroke-width="1" stroke-dasharray="4 4" opacity="0.5" />
                                <circle id="cursor-dot" cx="0" cy="0" r="6" fill="var(--bg)" stroke="var(--success)" stroke-width="3" />
                            </g>
                        </svg>
                    </div>
                    <div class="chart-controls">
                        <button class="chart-control-btn" onclick="updateTimeRange(this, '1D')">1D</button>
                        <button class="chart-control-btn" onclick="updateTimeRange(this, '1W')">1W</button>
                        <button class="chart-control-btn is-active" onclick="updateTimeRange(this, '1M')">1M</button>
                        <button class="chart-control-btn" onclick="updateTimeRange(this, '3M')">3M</button>
                        <button class="chart-control-btn" onclick="updateTimeRange(this, 'YTD')">YTD</button>
                        <button class="chart-control-btn" onclick="updateTimeRange(this, '1Y')">1Y</button>
                        <button class="chart-control-btn" onclick="updateTimeRange(this, 'All')">Max</button>
                    </div>
                </div>
            </main>

            <!-- Sidebar Details -->
            <aside class="investment-sidebar">
                <article class="detail-card">
                    <h3>Details</h3>
                    <div class="detail-list">
                        <div class="detail-item">
                            <span class="detail-item__label">NAV</span>
                            <span class="detail-item__value">$42,850.25</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-item__label">Cost Basis</span>
                            <span class="detail-item__value">$38,500.00</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-item__label">Cash</span>
                            <span class="detail-item__value">$1,200.50</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-item__label">Total Return</span>
                            <span class="detail-item__value detail-item__value--positive">+$4,350.25 (11.3%)</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-item__label">Account Type</span>
                            <span class="detail-item__value">Brokerage</span>
                        </div>
                    </div>
                </article>

                <article class="detail-card">
                    <h3>Cash Balance</h3>
                    <input type="text" class="cash-balance-input" value="1,200.50" />
                    <p class="u-muted u-small-note">Available for investment or transfer.</p>
                </article>
            </aside>
        </div>

        <!-- Holdings Section -->
        <section class="holdings-section">
            <header class="holdings-header">
                <h2>Holdings</h2>
                <button class="button button--secondary" id="toggle-holding-btn" onclick="toggleAddHolding()">+ Add Position</button>
            </header>

            <div class="add-holding-form" id="add-holding-form">
                <div class="form-panel__grid">
                    <div class="form-panel__field">
                        <label>Ticker</label>
                        <input type="text" placeholder="e.g. VTI">
                    </div>
                    <div class="form-panel__field">
                        <label>Quantity</label>
                        <input type="number" placeholder="0.00">
                    </div>
                    <div class="form-panel__field">
                        <label>Avg Cost</label>
                        <input type="number" placeholder="0.00">
                    </div>
                    <div class="form-panel__field">
                        <label>Current Price</label>
                        <input type="number" placeholder="0.00">
                    </div>
                </div>
                <div class="form-panel__actions">
                    <button class="button button--secondary" onclick="toggleAddHolding()">Cancel</button>
                    <button class="button button--primary" style="margin-left: 0.5rem;" onclick="toggleAddHolding()">Save Position</button>
                </div>
            </div>

            <div class="ledger-card">
                <table class="ledger-table">
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th class="ledger-table__amount">Qty</th>
                            <th class="ledger-table__amount">Price</th>
                            <th class="ledger-table__amount">Avg Cost</th>
                            <th class="ledger-table__amount">Market Value</th>
                            <th class="ledger-table__amount">Total Return</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="font-weight: 600;">VTI</td>
                            <td class="ledger-table__amount">150.00</td>
                            <td class="ledger-table__amount">$245.50</td>
                            <td class="ledger-table__amount">$210.00</td>
                            <td class="ledger-table__amount">$36,825.00</td>
                            <td class="ledger-table__amount detail-item__value--positive">+$5,325.00</td>
                        </tr>
                        <tr>
                            <td style="font-weight: 600;">VXUS</td>
                            <td class="ledger-table__amount">85.00</td>
                            <td class="ledger-table__amount">$56.80</td>
                            <td class="ledger-table__amount">$58.00</td>
                            <td class="ledger-table__amount">$4,828.00</td>
                            <td class="ledger-table__amount detail-item__value--negative">-$102.00</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>
    </div>

    <!-- MOCK JS LOGIC -->
    <script>
        // --- Mock Data Generator ---
        function generateChartData(points = 100, startVal = 40000) {
            let data = [];
            let val = startVal;
            const now = new Date();
            for (let i = 0; i < points; i++) {
                // Random walk
                val = val + (Math.random() - 0.45) * 500; 
                const date = new Date(now);
                date.setDate(date.getDate() - (points - i));
                data.push({ date: date, value: val });
            }
            return data;
        }

        let chartData = generateChartData(30);

        // --- Chart Render Logic ---
        const svg = document.getElementById('main-chart-svg');
        const pathLine = document.getElementById('chart-path');
        const pathArea = document.getElementById('chart-area');
        const cursorGroup = document.getElementById('cursor-group');
        const cursorLine = document.getElementById('cursor-line');
        const cursorDot = document.getElementById('cursor-dot');
        const tooltip = document.getElementById('chart-tooltip');
        const tooltipLabel = document.getElementById('tooltip-label');
        const tooltipValue = document.getElementById('tooltip-value');
        const selectionRect = document.getElementById('selection-rect');

        // ViewBox dimensions
        const VB_WIDTH = 1000;
        const VB_HEIGHT = 400;

        function renderChart() {
            const values = chartData.map(d => d.value);
            const min = Math.min(...values);
            const max = Math.max(...values);
            const range = max - min;
            // Add slight padding to Y-axis
            const padding = range * 0.1;
            const yMin = min - padding;
            const yMax = max + padding;
            const yRange = yMax - yMin;

            // Generate Path 'd' attribute
            let d = "";
            chartData.forEach((pt, i) => {
                const x = (i / (chartData.length - 1)) * VB_WIDTH;
                const y = VB_HEIGHT - ((pt.value - yMin) / yRange) * VB_HEIGHT;
                if (i === 0) d += `M ${x} ${y}`;
                else d += ` L ${x} ${y}`;
            });

            // Set Line Path
            pathLine.setAttribute('d', d);

            // Set Area Path (Close the loop at the bottom)
            // L to bottom-right, then to bottom-left, then close
            const dArea = d + ` L ${VB_WIDTH} ${VB_HEIGHT} L 0 ${VB_HEIGHT} Z`;
            pathArea.setAttribute('d', dArea);

            // Set Color based on Trend
            const start = chartData[0].value;
            const end = chartData[chartData.length - 1].value;
            const color = end >= start ? 'var(--success)' : 'var(--danger)';
            
            pathLine.setAttribute('stroke', color);
            cursorDot.setAttribute('stroke', color);
            
            // Update Gradient Stops
            document.getElementById('grad-start').setAttribute('stop-color', color);
            document.getElementById('grad-mid').setAttribute('stop-color', color);
        }

        // --- Interaction Logic ---
        const wrapper = document.getElementById('chart-wrapper');
        let isDragging = false;
        let startX = 0;
        let currentX = 0;

        function getChartPointFromX(clientX) {
            const rect = wrapper.getBoundingClientRect();
            let relativeX = clientX - rect.left;
            // Clamp
            relativeX = Math.max(0, Math.min(relativeX, rect.width));
            
            const ratio = relativeX / rect.width;
            const index = Math.round(ratio * (chartData.length - 1));
            
            return {
                index,
                data: chartData[index],
                svgX: ratio * VB_WIDTH,
                domX: relativeX,
                domY: rect.top // Needed for tooltip positioning?
            };
        }

        wrapper.addEventListener('mousemove', (e) => {
            const { index, data, svgX, domX } = getChartPointFromX(e.clientX);
            
            // Move Cursor
            cursorGroup.style.display = 'block';
            cursorLine.setAttribute('x1', svgX);
            cursorLine.setAttribute('x2', svgX);
            cursorDot.setAttribute('cx', svgX);
            
            // Calc Y for dot
            const values = chartData.map(d => d.value);
            const min = Math.min(...values);
            const max = Math.max(...values);
            const range = (max - min) * 1.2; // roughly match padding logic
            const yMin = min - (max-min)*0.1;
            const y = VB_HEIGHT - ((data.value - yMin) / range) * VB_HEIGHT;
            
            cursorDot.setAttribute('cy', y); // Approximate Y for visual snapping

            // Tooltip
            tooltip.classList.add('is-visible');
            tooltip.style.left = (domX + 15) + 'px';
            // Simple static top position for tooltip or follow Y
            tooltip.style.top = '20px'; 
            
            const fmtVal = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(data.value);
            const fmtDate = new Date(data.date).toLocaleDateString();

            if (isDragging) {
                // Measure Mode
                const startPoint = getChartPointFromX(wrapper.getBoundingClientRect().left + startX);
                const diff = data.value - startPoint.data.value;
                const pct = (diff / startPoint.data.value) * 100;
                const sign = diff > 0 ? "+" : "";
                
                tooltipLabel.innerText = `${new Date(startPoint.data.date).toLocaleDateString()} – ${fmtDate}`;
                tooltipValue.innerText = `${sign}${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(diff)} (${sign}${pct.toFixed(2)}%)`;
                
                // Draw Selection Rect
                const dragWidth = domX - startX;
                // Convert DOM x to SVG x
                const rectX = Math.min(startX, domX) / wrapper.getBoundingClientRect().width * VB_WIDTH;
                const rectW = Math.abs(dragWidth) / wrapper.getBoundingClientRect().width * VB_WIDTH;
                
                selectionRect.style.display = 'block';
                selectionRect.setAttribute('x', rectX);
                selectionRect.setAttribute('width', rectW);

                // Update Color dynamically based on selection
                const color = diff >= 0 ? 'var(--success)' : 'var(--danger)';
                pathLine.setAttribute('stroke', color);
                document.getElementById('grad-start').setAttribute('stop-color', color);
                document.getElementById('grad-mid').setAttribute('stop-color', color);

            } else {
                // Standard Hover
                tooltipLabel.innerText = fmtDate;
                tooltipValue.innerText = fmtVal;
            }
        });

        wrapper.addEventListener('mousedown', (e) => {
            const rect = wrapper.getBoundingClientRect();
            startX = e.clientX - rect.left;
            isDragging = true;
        });

        document.addEventListener('mouseup', () => {
            if(isDragging) {
                isDragging = false;
                selectionRect.style.display = 'none';
                // Reset color to total range trend
                const start = chartData[0].value;
                const end = chartData[chartData.length - 1].value;
                const color = end >= start ? 'var(--success)' : 'var(--danger)';
                pathLine.setAttribute('stroke', color);
                document.getElementById('grad-start').setAttribute('stop-color', color);
                document.getElementById('grad-mid').setAttribute('stop-color', color);
            }
        });

        wrapper.addEventListener('mouseleave', () => {
            if(!isDragging) {
                cursorGroup.style.display = 'none';
                tooltip.classList.remove('is-visible');
            }
        });

        // --- Controls Logic ---
        function updateTimeRange(btn, range) {
            // Visual Active State
            document.querySelectorAll('.chart-control-btn').forEach(b => b.classList.remove('is-active'));
            btn.classList.add('is-active');

            // Generate new data based on range
            let points = 30;
            if(range === '1D') points = 24; // Hours
            if(range === '1W') points = 7;
            if(range === '3M') points = 90;
            if(range === 'YTD') points = 120; // Mock
            if(range === '1Y') points = 365;
            
            chartData = generateChartData(points, 40000);
            renderChart();
        }

        function toggleAddHolding() {
            const form = document.getElementById('add-holding-form');
            const btn = document.getElementById('toggle-holding-btn');
            if (form.classList.contains('is-visible')) {
                form.classList.remove('is-visible');
                btn.innerText = "+ Add Position";
            } else {
                form.classList.add('is-visible');
                btn.innerText = "Cancel";
            }
        }

        // Initialize
        renderChart();

    </script>
</body>
</html>
```
