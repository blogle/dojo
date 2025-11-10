Forecasting and Scenario Analysis

The Forecasting domain is the application's engine for long-term strategic planning, enabling users to evaluate the future impact of current financial decisions and model various "What-If" scenarios.

Core Objectives

The primary goal is to provide actionable financial longevity. This is achieved by projecting the probability distribution of future net worth over an extended time horizon. This moves the financial planning exercise beyond simple linear extrapolation and into robust, risk-aware statistical modeling.

Inputs and Model Sourcing

The forecasting process requires three key inputs:

First, it requires the Current Financial State, including the current net worth and the historical spending profile, which is supplied directly by the Net Worth domain through a complex analytical query against the temporal transaction data. This spending profile establishes the baseline cash flow for the projection.

Second, the domain consumes external model artifacts from the Quantitative Modeling Harness. This includes validated, versioned output such as estimated investment return moments (expected return, volatility, correlation matrix) and parameters for statistical models. This strict separation ensures that all models used for forecasting are rigorously tested before being deployed.

Third, it receives User Scenarios, which are hypothetical changes requested by the user. These could involve increasing savings rates, making a large one-time purchase, adjusting income streams, or paying off a mortgage early.

Projection and Scenario Evaluation

The Forecasting module utilizes quantitative models and statistical methods to project future wealth. This may include parametric approaches like Monte Carlo simulations, historical bootstrapping, or non-parametric techniques, depending on which model was promoted by the Modeling Harness. The core mechanism is to simulate thousands of plausible economic futures, factoring in investment returns, planned contributions, and the historical spending profile, to determine the likely range of net worth outcomes.

When a user submits a scenario, the module immediately adjusts the parameters of the baseline simulation. For example, doubling a grocery budget immediately reduces the future discretionary cash flow in the model, allowing the user to see the precise, quantifiable impact of that spending change on the probability of reaching a financial goal decades in the future.

Output and Presentation

The output of the forecasting engine is a probability distribution, which is communicated to the user via two key visualization formats:

Projected Equity Curves: This includes the expected median (50th percentile) net worth, alongside conservative (e.g., 5th percentile) and optimistic (e.g., 95th percentile) outcomes at various stages of the user's life. This provides a clear range of potential wealth accumulation.

Probability of Target Wealth: This specialized visualization allows the user to input a specific dollar amount (the target wealth) and then displays the probability of the household having at least that amount of money at any given point in the projection horizon. Using this visualization with an input value of zero (or a negative liability threshold) provides the critical probability of ruin over the projection period, offering a precise measure of financial security.

This probabilistic view provides a much clearer picture of financial risk than traditional single-point forecasts.
