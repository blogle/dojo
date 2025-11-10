Portfolio Optimization and Advisory

This domain provides the active advisory layer of the application, translating complex quantitative models into actionable rebalancing and asset allocation guidance for the user's portfolio.

Core Objectives

The primary goal is to provide data-driven investment guidance by defining a target portfolio allocation and minimizing the behavioral and tax costs associated with reaching it. This ensures that investment decisions are aligned with the household’s risk tolerance and long-term financial goals.

The Target Portfolio Allocation

The target allocation is determined by loading a validated optimization model (e.g., a Mean-Variance Optimization or Factor Model) from the Quantitative Modeling Harness artifact directory. This model is applied to the Watchlist of available securities provided by the Investments domain.

The allocation process rigorously adheres to user-defined constraints:

Non-Self-Directed Accounts: Positions held in employer-sponsored plans or accounts managed by external advisors are treated as hard lower and upper bounds on the asset weights. The optimization engine cannot recommend trades that would violate these existing positions.

Self-Directed Accounts: These accounts are subject to full optimization, aiming to compensate for the fixed positions in the constrained accounts while still hitting the overall target asset class weights.

The result is the Target Portfolio, an ideal asset weighting across all tracked securities that serves as the benchmark for comparison.

Tracking and Monitoring Deviation

The system tracks two critical measures of performance:

Actual Performance vs. Benchmark: How the current, actual portfolio performs against external benchmarks like the S&P 500.

Actual Performance vs. Target Portfolio: How the actual portfolio (which may deviate for tax or preference reasons) performs against the model-derived Target Portfolio. This provides a direct measure of the cost or benefit of active decision-making.

A key output is a Deviation Analysis that highlights which asset classes and individual holdings deviate most significantly from the Target Portfolio, triggering a review.

Advisory and Rebalancing Guidance

When the deviation from the Target Portfolio exceeds a predefined threshold, the domain generates specific rebalancing recommendations. This guidance is prioritized to be tax-efficient:

The system prioritizes trading within tax-advantaged accounts (IRAs, 401ks) first, as sales in these accounts do not trigger capital gains tax events.

For taxable accounts, the system identifies opportunities for Tax-Loss Harvesting, recommending the sale of positions with unrealized losses to offset current or future capital gains, thus minimizing the immediate tax burden.
