# Portfolio Evaluation and Backtesting Framework Architecture

This document defines the architecture, core components, and governing principles of the quantitative evaluation harness. This framework, referred to as the `BacktestEngine`, is designed to provide a reproducible and statistically rigorous assessment of investment strategies against historical and synthetically augmented market data.

## 1. Principles of Design

The architecture is built on three foundational pillars to ensure the integrity of financial research:

### Reproducibility and Auditability

Every evaluation must be fully reproducible. This is achieved by binding a run to a single, immutable `Experiment` configuration and persisting all inputs and outputs (market data references, strategy parameters, and performance metrics) to a dedicated, versioned database.

### Statistical Rigor

The system must actively guard against look-ahead bias and overfitting. This is enforced through a mandatory **Purged, Embargoed Cross-Validation (PECV)** scheme, where test sets are explicitly separated from train sets by a "purge" period, and subsequent test sets are separated by an "embargo" period.

### Data Skepticism (Augmentation)

The introduction of synthetic or backfilled market data is treated as a high-risk operation. Synthetic data must first pass an independent **Placebo Testing** framework before it is permitted as input for official strategy backtesting. Crucially, synthetic data is generated into a temporary, non-persistent staging area and is **never** commingled with real market data within the core `MarketStore`. This ensures the canonical store of verified market history remains untainted.

## 2. Core Components and Interfaces

The evaluation harness is composed of seven primary components, each responsible for a distinct phase of the backtesting lifecycle.

### `Experiment` (YAML Configuration)

The `Experiment` is the definitive, top-level contract for any evaluation run. It is a structured YAML file that defines the entire environment, including:

-   **Market Universe**: The equity basket, risk-free rate source, and the historical start and end dates.
-   **Backtest Specification**: Parameters for the PECV scheme (window, test, purge, and embargo percentages).
-   **Data Sourcing**: References to the primary `MarketStore` database (real data) and the target `Experiment DB` for results persistence.
-   **Strategies**: A list of specific strategies to be evaluated, along with their unique hyperparameters.
-   **Augmentation (Optional)**: Configuration parameters for enabling and initializing a synthetic data `Augmentation` model.

### `MarketStore` (Canonical Time Series)

The `MarketStore` is an embedded financial time-series database implemented within DuckDB. It operates as a read-through cache for all required market data.

-   **Data Sourcing**: If the required symbols and dates are not present in the database, the `MarketStore` automatically triggers a back-fill operation, requesting the necessary data from external sources (e.g., `yfinance`).
-   **Invariance**: The `MarketStore` holds the canonical, non-synthetic market history. It can utilize previously validated augmented data during a run to satisfy a query but **never** persists the raw synthetic output into its core tables alongside the real market data.

### `Augmentation` (Interface)

This is an implementable interface used for generating synthetic market data to back-fill insufficient history for assets (e.g., TSLA, VOO).

-   **Data Flow**: Generated synthetic data is output to a temporary staging environment (e.g., an in-memory DuckDB instance or a non-persistent file). This staged data is used exclusively by the **Placebo Testing** framework to validate its quality.
-   **Purpose**: Allows strategies to be evaluated across a broader set of market regimes by fitting models (e.g., Monte Carlo, MCMC, Factor Models) to existing history.

### `Strategy` (Interface)

This is the core behavioral interface, defining the specific method for allocating available capital among the assets in the evaluation universe. Any portfolio selection model must implement this interface, typically exposing `fit()` and `predict()` methods for use within the cross-validation process.

### `Pipeline`

The `Pipeline` is the simulation runner. It executes a specified `Strategy` over a given window of market data.

-   **Execution**: It takes the strategy's weight outputs at each time step and simulates the portfolio's performance over the test window, accounting for transaction costs and slippage (if configured).
-   **Metric Collection**: During execution, the `Pipeline` collects and maintains a single instance of the `PerformanceMetrics` class for the specific strategy and evaluation fold.

### `PerformanceMetrics`

This component is a container responsible for storing and calculating common performance statistics for a single strategy's equity curve. Metrics calculated adhere strictly to the rules defined in the **Financial Math Standards** and include, but are not limited to:

-   Equity Curve (Time-series of simple returns).
-   Risk Metrics: Volatility, Conditional Value-at-Risk (CVaR).
-   Ratio Metrics: Sharpe Ratio, Sortino Ratio.
-   Drawdown Analysis.

### `BacktestEngine` (The Evaluation Harness)

The `BacktestEngine` is the top-level orchestrator that executes the entire evaluation specified by the `Experiment` configuration.

-   **Initialization**: It first ensures all required market data is present in the `MarketStore`, triggering back-filling and only accessing previously validated augmented data if configured.
-   **CV Splitting**: It computes the deterministic train/test splits based on the PECV parameters, ensuring the window and test sizes are the target sizes after applying the required purge and embargo periods.
-   **Orchestration**: It systematically runs the `Pipeline` for every strategy across every cross-validation fold.
-   **Persistence**: The final, fold-specific results (including trade logs and the `PerformanceMetrics` object) are persisted to the designated `Experiment DB` (DuckDB or Parquet file) for later roll-up and analysis.

## 3. Execution Flow and Data Integrity

The backtesting process is highly structured to guarantee deterministic outcomes and data integrity.

### Atomic Persistence

All write operations, from fetching data into the `MarketStore` to persisting final results into the `Experiment DB`, are managed transactionally. The `BacktestEngine` acquires a file-based lock on the target database before execution and releases it only upon a successful commit or a complete rollback in case of failure. This prevents concurrent writes and ensures the integrity of the persistent results.

### The Purged, Embargoed Cross-Validation (PECV)

The core simulation loop relies on PECV to prevent look-ahead bias:

-   **Window Calculation**: The `BacktestEngine` translates the user's window, test, purge, and embargo percentages into exact trading day counts.
-   **Purge**: After a fold's training period, a purge period is strictly enforced, meaning the strategy cannot be evaluated on data immediately following its training period. This prevents bias from overlapping information due to dependencies like short-term volatility or volume features.
-   **Embargo**: After the test period for a fold, an embargo period is enforced before the next training period can begin. This prevents the training set of a subsequent fold from being contaminated by knowledge gained from the prior fold's test outcomes.

### Results Aggregation

Once all strategies have been run across all folds, the `BacktestEngine` performs a final aggregation query against the persisted fold data in the `Experiment DB`. This allows for cross-strategy comparison, statistical testing (such as the Reality Check (RC) and Superior Predictive Ability (SPA) tests), and the generation of a final, summarized report that consolidates the performance metrics across all evaluation folds.
