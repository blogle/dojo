# Investment Tracking

This domain manages all activities related to tracking and analyzing the investment portfolio, ensuring that asset performance is accurately integrated into the overall net worth calculation.

## Core Entities and Data Model

The investment domain relies on the temporal tracking of individual asset holdings and the current status of the market.

The `Positions` entity is the primary temporal table in this domain. It tracks the individual holdings within each investment account. Every time a trade is executed, or an entry is corrected, the record is versioned. Each version records the security symbol, the number of shares held, the average cost basis for those shares, and the associated investment account. The temporal nature of this table ensures that historical performance metrics can be calculated correctly based on the holdings at any given past date.

The `Securities` entity acts as a stable state table, storing identifying information for all securities tracked by the application, such as the unique symbol, the full company name, and the exchange on which it trades. This entity also tracks a Watchlist, which includes all securities currently held in any account, along with any other securities the user is interested in analyzing or considering for investment.

The `Accounts` entity, shared with the Budgeting domain, is critical here, but with specific investment context. It tracks the type of investment account (e.g., brokerage, tax-advantaged retirement plan, or employer-sponsored 401k). This classification is used to determine which accounts are self-directed and which must be treated as fixed bounds during the portfolio optimization process.

## Key Operational Flows

### External Data Ingestion and Pricing

A scheduled background process handles the daily ingestion of external market data. This process connects to external financial data providers to retrieve the latest market pricing for all tracked securities and those on the Watchlist. This price information is then used to calculate the real-time market value of all active positions. Historical price data is stored locally to ensure reliable, high-speed calculation of performance metrics without dependence on live API calls during reporting.

### Performance Analysis

The application runs internal analytics to calculate a comprehensive suite of performance metrics for all accounts, as well as the aggregate portfolio. These metrics include total returns, risk (volatility), the Sharpe ratio, and historical drawdowns. These performance figures are calculated both for individual accounts and across the entire portfolio. This analysis is crucial for comparing the portfolio's actual performance against predetermined external benchmarks, such as the S&P 500, providing an objective measure of success.

### Data Preparation for Optimization

The Investments domain is responsible for generating a comprehensive snapshot of all current holdings and securities for consumption by the separate Optimization domain. This includes the precise number of shares, the current market value, the tax status of each holding (long-term gain, short-term gain, loss), and the designation of whether the account is self-directed or constrained.
