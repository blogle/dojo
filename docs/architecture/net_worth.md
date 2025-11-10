Net Worth and Aggregation

The Net Worth domain serves as the central synthesis point of the application, aggregating data from all other modules to provide a single, comprehensive view of overall financial health and wealth preservation progress.

Core Concept and Objectives

The core concept is the net worth equation: Total Assets minus Total Liabilities equals Net Worth. The objective of this domain is to calculate this metric accurately, present it prominently, and enable high-speed historical analysis. Because the ultimate goal of the application is wealth preservation and accumulation, net worth is positioned as the primary metric.

Data Sourcing and Calculation Logic

The Net Worth calculation is a derived metric, but to ensure optimal user experience, its history is materialized.

The Materialized History Table

To address performance concerns for high-speed reporting, the domain maintains a dedicated, non-temporal table called NetWorthHistory. This table stores a daily snapshot of the total Net Worth value and key components (Total Assets, Total Liabilities) calculated at the end of that day.

A scheduled background process runs a complex analytical query once per day (or on demand):

The query leverages the temporal Transactions and Positions tables to accurately reconstruct the net worth value as of the calculation time.

The resulting aggregated value is then inserted into the simple, indexed NetWorthHistory table.

This pre-calculated history table allows the application to retrieve time-series data for historical charts, volatility analysis, and trend reporting almost instantaneously, avoiding the need to run computationally expensive bitemporal joins on every user request.

Current State Dashboard

The instantaneous current net worth value for the main dashboard is still calculated by fetching the current active balances from the Accounts and Positions tables. This single, highly optimized query remains fast and guarantees the user sees the absolute latest value.

Key Flows and Output

Net Worth History Reporting

The domain provides reporting endpoints that query the NetWorthHistory table to display the time series of the net worth. Key outputs include:

Trending: Visualization of net worth over user-defined time periods.

Volatility: Analysis of the historical fluctuation of the net worth.

Current State: The most recent net worth value, clearly differentiated from the historical trend data.

Baseline Data for Forecasting

This domain acts as a data pipeline for the Forecasting module. It provides the essential baseline inputs required for future projections, including the current total net worth and a robust historical measure of the household's discretionary spending (or burn rate), which is derived from aggregating and analyzing the underlying historical transaction data. This clean, aggregated historical input is crucial for the reliability of all long-term forecasts.
