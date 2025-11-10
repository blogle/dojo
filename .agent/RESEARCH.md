# Research Specifications (ExecResearch)

This document defines "ExecResearch": a structured, living research artifact that an engineer or AI agent can use to explore an open-ended question, run experiments, record findings, and converge on an actionable recommendation. An ExecResearch file is meant to be dropped into a repository and picked up by the next contributor with no additional context. It exists to reduce wandering, prevent forgotten insights, and ensure research work is reproducible, auditable, and decision-driving.

ExecResearch is not a proposal for future work in the abstract. It is an operational research journal and lab notebook with instructions. It names concrete questions to answer, describes how to answer them, captures the evidence that was gathered, documents why certain branches were pursued or abandoned, and states how to verify and reproduce every result.

If a RESEARCH.md file is checked into the repo, reference its path from the repository root in this section and state that ExecResearch documents must be maintained in accordance with RESEARCH.md. If RESEARCH.md is not checked in, this ExecResearch must include all necessary guidance itself and cannot assume the reader has access to any other document.

## How to Use ExecResearch and RESEARCH.md

ExecResearch is the working surface for a single research direction. It lives alongside code and evolves as experiments run, ideas are tested, and evidence accumulates. It should always reflect the current state of understanding for this research direction and should always tell the next researcher what to try next and why.

Treat the ExecResearch file as the source of truth for:

1. Problem framing
   The specific question we are trying to answer, why it matters, and what "useful" means in this context.

2. Research plan
   The methods we intend to try, what they are expected to demonstrate, and how we will measure success or failure.

3. Experimental log
   The experiments we actually ran, with enough detail that anyone can re-run them and get matching or explainable results.

4. Running interpretation
   How the evidence is changing our beliefs. What has been ruled out, what looks promising, and what is still unknown.

5. Decision trail
   When we branch, pivot, or abandon an approach, we record that choice and why. This prevents repeating dead ends and preserves the reasoning behind promising directions.

RESEARCH.md (if present) is the index of active and past research efforts. It can summarize multiple ExecResearch documents and help decide priority. ExecResearch is not a summary. ExecResearch is the lab bench. It must stay up to date as work proceeds — it is a living document, not a frozen spec.

Hand-off expectation: You must be able to hand this file alone to a new engineer or agent — with zero in-person onboarding — and they should be able to (1) understand the active question, (2) rerun validated experiments, (3) continue the next planned experiment, and (4) avoid repeating known mistakes.

## Requirements

The following requirements are non-negotiable for every ExecResearch:

1. Self-contained
   The ExecResearch file must contain all definitions, assumptions, metrics, data references, and procedures needed for a novice to pick up the work. Do not assume any prior discussion, meeting notes, Slack threads, or tribal knowledge. If you must reference other code or data, use unambiguous repository-relative paths and describe what is in them and why they matter.

2. Living and current
   The document must be maintained as experiments complete, interpretations evolve, and decisions are made. Stale or wishful content is a failure. Every material change to thinking, direction, or conclusion must be reflected in the document itself, including rationale.

3. Reproducible
   Every experiment described here must include: data inputs, preprocessing steps, configuration, parameters, code entry points, seeds or determinism strategy, and the exact commands to run. A future contributor must be able to replicate results and confirm they match (or understand and explain drift).

4. Action-oriented
   Research must drive toward an answer someone can build on. The goal is not academic novelty. The goal is to converge on "what should we build next and why," with evidence.

5. Evaluation-defined
   All claims must be supported by objective evaluation criteria stated in advance. State which metrics matter, how they are computed, and how to interpret them. Do not redefine success after seeing results unless you explicitly record that decision and why.

6. Anti–data snooping
   All evaluation must be structured to avoid fooling ourselves. This includes proper train/test splits, isolation of holdout sets, walk-forward validation for time series, and any other safeguards appropriate to the domain. You must document how leakage was prevented.

7. Evidence captured
   Observed metrics, plots, console output, commit SHA's, diffs, or summaries of runs must be included in the ExecResearch file in concise quoted or indented excerpts. Observations must be linked to specific experiment identifiers so they can be repeated and extended.

8. Next steps always clear
   At any point, the document must state the next experiment(s) to run and why they matter. If the research is considered "sufficiently answered," the document must explicitly say so and must summarize the recommendation for productionization or follow-on work.

## Formatting

ExecResearch is written as a single fenced code block labeled `md` that begins and ends with triple backticks. This allows an agent or engineer to lift the entire content directly into a `.md` file with no further transformation. Because the entire ExecResearch is already inside a triple-fenced block, do not introduce nested triple-backtick fences inside. Whenever you need to show commands, logs, diffs, code snippets, tables of metrics, or data samples, present them as indented blocks using four leading spaces. This prevents accidentally closing the main fence.

When writing an ExecResearch file directly to disk as a `.md` file (the file content is only the ExecResearch and nothing else), you should omit the outer triple backticks and write normal Markdown. When returning an ExecResearch document inline (for example, as a model response), always include the triple-fenced `md` block.

Headings must follow standard Markdown heading levels (`#`, `##`, `###`, etc.). Insert two blank lines after every heading to keep sections visually distinct and easy to parse for automated agents.

Write in plain English prose wherever possible. Use lists sparingly. Lists are acceptable in sections specifically called out below for structured logging (for example, in "Progress & Experiment Log" or "Decision Log"), but otherwise narrative text should lead.

All timestamps must be explicit and include date and 24-hour time with UTC offset, for example: `2025-11-07 16:20Z`. If local-time assumptions matter (for example, a batch job depends on market close), record local time as well and name the timezone.

## Guidelines

### Self-containment

Define every specialized term the first time you use it, in plain language. For example, if you refer to "synthetic backfill," spell out exactly what that means (for example: "Synthetic backfill means generating plausible historical data for an asset or metric before we have real observations, so downstream models can train on longer series"). Avoid unexplained shorthand like "MVO" or "CPPI" unless you also define it in this document.

If a concept is mathematical or statistical (for example, "walk-forward validation"), describe how we actually apply it in this project: which windows, which splits, which leakage concerns.

### Actionable research

Do not write vague aspirations like "explore better allocation strategies." Instead, write testable questions such as: "Does a downside-risk-aware portfolio allocation method (using conditional drawdown at risk instead of variance) reduce simulated worst-case 1-year drawdown compared to baseline mean-variance optimization under our retirement withdrawal model?" Then explain how you will measure that.

Every experiment must trace back to a question the business/product actually cares about. "Product cares about X" should be stated explicitly in "Problem Framing & Research Goal."

### Reproducibility

You must describe how to re-run each experiment exactly. That includes:

- Which dataset(s) or table(s) to load, with full repository-relative paths.
- The filters or time ranges used.
- Any sampling, shuffling, or augmentation and the random seeds.
- The training/evaluation split and why that split is valid.
- The parameters or hyperparameters (for example, "learning_rate=0.001", "regularization_strength=0.1").
- The command(s) or script invocation(s) required to reproduce.
- Any environment assumptions (for example, "requires CUDA GPU," "requires DuckDB >= 1.1.0," "requires pandas >= 2.2").

When results differ across hardware or runs, note the tolerance we consider "the same" (for example, "Sharpe ratio within ±0.02 is considered equivalent") and why that tolerance is acceptable.

### Evaluation and leakage safety

For each metric you report, define:

- What does this metric measure in plain language?
- Why does this metric matter to us?
- How is it computed? Include formulas or step-by-step description if needed.
- What does "good" look like, in numbers?
- How do we prevent cheating? For example, for time series forecasting, we cannot allow any future data in the training window when evaluating past periods. State exactly how you enforce that.

This protects us from "data snooping," which is when you accidentally tune to information you shouldn't have, like peeking at future returns while designing a predictor of future returns. You must explicitly describe controls against this.

### Evidence, not vibes

Any claim like "Method B is more stable" must cite an experiment result. That result must live in "Progress & Experiment Log," and that log must include observable outputs (for example, a small indented table of drawdowns per simulation seed, or a summary like "max 12-month peak-to-trough loss improved from -34% to -27% in 10,000 Monte Carlo trials").

### Orientation and hand-off

ExecResearch must be written for someone who is intelligent and motivated, but unfamiliar with this repository and this problem. They should be able to show up with no context, read top-to-bottom, and know where to continue. That future reader might be human, or an AI agent acting as a research assistant. Both will depend on this file.

## Problem Framing & Research Goal

This section explains, in a few paragraphs, what we are trying to figure out and why it matters.

You must answer, in plain language:

1. What practical capability will we unlock if this research succeeds?
   ("Planners will be able to backfill missing asset histories for niche ETFs with synthetic but statistically consistent data, so we can run our retirement simulations on longer horizons instead of throwing away entire tickers with <5 years of history.")

2. How will we know we're done?
   ("We're done when we can generate backfilled price histories that are indistinguishable from real histories along drift, volatility, and tail-risk metrics across rolling windows, and an end-to-end simulation using those backfilled assets produces no more than X% deviation in worst-case drawdown compared to the same simulation run on real data for assets where we do have full history.")

3. Where does this research live in the product?
   ("This feeds the portfolio simulator used in retirement planning. If the simulator cannot trust the inputs, the advice is misleading. This research is therefore safety-critical for user outcomes and compliance.")

This section sets the stakes. It must be understandable by a non-technical stakeholder reading only this file.

## Prior Art & Background

This section summarizes approaches we already know about, both internal and external. "Prior art" means any known technique, model, heuristic, or baseline. This includes:

- Techniques we already use today (for example, "We currently use simple linear regression on peer assets to infer missing history").
- Techniques we tried before and abandoned, and why.
- Techniques from published literature or common industry practice that are relevant.
- Vendor APIs, libraries, or toolkits we could leverage.

Each technique should be described in our own words, not by linking to an external blog post or paper. If you use a name like "Black-Litterman" or "CPPI," define it. For example:

    Black-Litterman: A portfolio construction approach that starts with a baseline 'market equilibrium' portfolio and then nudges expected returns toward investor views, producing more stable and diversified weights than pure mean-variance optimization.

For each approach, explicitly state:

- Does this technique plausibly solve our problem?
- Have we already validated it in our environment?
- If yes, where is evidence captured in "Progress & Experiment Log"?
- If no, do we plan to validate it in small form? Where is that planned?

This background section should also call out constraints that are unique to us. For example: "Our simulator requires daily observations with no gaps, and assumes simple returns (percentage change), not log returns. Any method that outputs only monthly or log-scale series will require an adapter layer, which must be evaluated for bias."

If you believe an approach is unsafe or unsuitable, say so, and say why. Do not silently ignore it.

## Research Plan & Experiment Design

This section lays out the structured plan of attack. It is not the experiment log; it's the playbook.

Explain, in prose:

1. The key hypotheses or questions we intend to test.
   ("Does augmenting thin-asset histories using a factor model plus noise sampling preserve drawdown characteristics under Monte Carlo stress?")

2. The experimental method(s) we will use to answer each hypothesis.
   For each planned experiment, define:
   - Input data and how it is prepared.
   - The transformation/model/algorithm being tested.
   - The evaluation procedure and metrics.
   - The acceptance criteria that would count as 'promising' or 'rejected'.

3. The safeguards against fooling ourselves.
   - How we prevent data leakage.
   - How we enforce out-of-sample validation.
   - How we track seeds and environment.

4. The incremental sequence.
   - Which experiment runs first, and what decision it will unblock.
   - What we expect to promote or drop after each step.
   - Where we expect to pivot if a result is bad.

This section should read like a roadmap for the next day or week of research. Someone should be able to follow it step by step.

### Small-Scale Validation / De-risking

For any high-risk or high-effort idea, define a minimal "spike" experiment: the smallest runnable test that can prove "this is viable" or "this is not worth pursuing." The spike should require the least possible engineering investment while still producing objective evidence.

Describe, for each spike:

- What we will build or run.
- The minimal data slice or time window it will operate on.
- The expected signal ("if we can't even get X > baseline on this tiny slice, we should not invest a week building it full-scale").
- Exactly how to run it and what output proves success.

Spikes are how we avoid wasting large blocks of time on pretty ideas that die on first contact with reality.

## Progress & Experiment Log

This is the living heartbeat of ExecResearch. It is always current.

This section is a chronological log of experiments that actually happened. Every time we run, extend, or interpret an experiment, we add an entry here. Each entry must include:

- Timestamp (UTC) of the run or interpretation.
- Experiment label or identifier (short but stable, e.g. "EXP-03-volatility-matching").
- What we did (data, method, parameters).
- The observed results (metrics, console output excerpts, etc.).
- Interpretation (what we learned, how this changes our beliefs, and what we plan to do next).

Use a list with checkboxes to indicate experiment status. Checked means "complete and captured." Unchecked means "planned, not yet run" or "in progress." This gives at-a-glance status to the next contributor.

Example structure for entries in this section:

- [x] (2025-11-07 16:20Z) EXP-03-volatility-matching
      Goal: Match daily volatility profile of synthetic backfilled prices to real data over rolling 30-day windows.
      Data: assets/us_equities/SPY.csv (2010-2020) as reference; synthetic generated for TICKER_X from factor model with noise seed 42.
      Method: Calibrated factor loadings using 2015-2017 window, froze them, generated forward, no peeking past 2017.
      Result:
          max absolute volatility gap across 30-day windows: 0.0041
          median gap: 0.0012
          worst drawdown deviation in Monte Carlo sim: -27.3% synthetic vs -28.1% real
      Interpretation: Gaps are within tolerance (<0.005) and drawdown behavior is close enough to consider viable for planning sims. Promoted this method to "candidate" status. Next: run EXP-04 to test tail risk under recession-like shock.
      Reproduce:
          Run from repo root:
              (1) activate venv with requirements.txt
              (2) python tools/synth_backfill.py --target TICKER_X --seed 42 --calibration-window 2015-01-01:2017-12-31
              (3) python eval/simulate_drawdown.py --asset TICKER_X --horizon 365d --mc_iters 10000 --seed 123
          Expected: summary table with 'worst_drawdown' lines similar to numbers above.

- [ ] EXP-04-stress-tailrisk
      Planned. Will inject 2008-style crisis shock into both real and synthetic series and compare 95th percentile drawdown and recovery half-life. Acceptance: synthetic must not understate losses by more than 3 percentage points.

This log replaces hallway updates, Slack messages, and ad hoc screenshots. If it matters, it goes here.

## Surprises & Discoveries

This section captures unexpected behavior, system quirks, optimizer effects, pathological cases, directional insights, or anything else that changed how we think about the problem.

Each item should include:

- Observation: what we saw.
- Evidence: short, concrete proof (numbers, short console output, etc.).
- Impact: how this changes our direction, if at all.

For example:

- Observation: Synthetic backfill using naive linear peer regression produced unrealistically smooth drawdowns, which tricked the risk model into underestimating worst-case 1-year loss.
  Evidence:
      worst 365d drawdown (real SPY 2015-2020): -32.4%
      worst 365d drawdown (synthetic peer-fit): -21.7%
      The synthetic never captured a fast crash-and-snapback event.
  Impact: We cannot rely on this regression method alone. We need to inject jump-like shocks that mimic crisis regimes. Added EXP-05 to design and test shock injection.

Do not hide awkward results. Surprises are often the most valuable output of research. They prevent future repeat mistakes.

## Decision Log

This section records the forks in the road. Every time we decide to pursue, de-prioritize, or abandon a path, we log it here.

Each decision entry must include:

- Decision: what we chose.
- Rationale: why we chose it, in plain terms.
- Date/Author: timestamp and who made the call (engineer, reviewer, or agent identity).
- Evidence reference: which experiment(s) from "Progress & Experiment Log" supported that call.

Example:

- Decision: Adopt volatility-calibrated factor backfill (EXP-03) as the working candidate method for thin-history tickers.
  Rationale: It matched drawdown characteristics within tolerance and ran fast enough for batch ingestion.
  Date/Author: 2025-11-07 17:10Z / research-agent-alpha
  Evidence reference: EXP-03-volatility-matching results showed drawdown deviation under 1 percentage point.

- Decision: Drop naive peer regression backfill.
  Rationale: It systematically understated crash severity, which creates user-harm and compliance risk.
  Date/Author: 2025-11-07 17:25Z / research-agent-alpha
  Evidence reference: Surprise entry "understated tail risk in peer regression" and EXP-02-peerfit-gap.

This log is critical. It prevents future contributors from resurrecting an already-rejected path without understanding why it was rejected.

## Interim Conclusions & Recommendations

This section summarizes what is currently believed to be true and what we recommend doing next in product or engineering terms.

This does not need to wait until "the end." Update it whenever your working recommendation changes in a meaningful way.

You must answer:

1. What approach currently looks most promising, and why?
2. What are its known weaknesses or open questions?
3. What additional evidence is required before we can safely ship or depend on it?
4. Is that evidence already planned as an experiment in "Progress & Experiment Log"? If not, add it.

If a direction is "good enough to integrate into production behind a feature flag," state that explicitly and describe what guardrails or monitoring would be required.

If the direction is "not viable; we should abandon," say that too, and explain what made it non-viable.

## Reproducibility & Environment Assumptions

This section defines the environment and determinism strategy required to reproduce experiments. This is not just "run pip install." It is the authoritative recipe for re-running and extending this work predictably.

Include:

1. Runtime environment
   - Language versions (for example, "Python 3.12.1").
   - Critical libraries and their versions (for example, "pandas 2.2.x", "numpy 2.x", "duckdb 1.1.x").
   - Hardware assumptions (for example, "NVIDIA GPU with CUDA 12.x available" or "CPU-only is acceptable; expect 4–6 minute runtime per experiment").
   - External services or data sources required (for example, "historical_price_cache.duckdb in data/ must exist with daily OHLCV for SPY and peer assets").

2. Determinism
   - How seeds are set (for example, "all Monte Carlo sims must pass --seed <int> and must not use unseeded NumPy RNG calls").
   - How data splits are fixed and reused across experiments (for example, "train/test cut at 2018-01-01 for all EXP-0x-* experiments; never move this cut without explicitly logging a new cut in Decision Log").
   - Tolerances for floating-point drift.

3. Command patterns
   - The canonical way to invoke experiments (for example, "run python eval/simulate_drawdown.py with the same --params.json file committed in research/params/EXP-03.json").
   - Where outputs should be written (for example, "write per-run results to research/runs/EXP-03/ so future contributors can diff metrics over time").

Without this section, reproducibility fails, and the research cannot be trusted.

## Risk, Ethics, and User Impact

This section explicitly states any way the research could mislead users, worsen outcomes, or create regulatory/compliance exposure if adopted naively.

Examples:

- "These backfilled asset histories may make niche assets look artificially stable, which could convince a user they are safe to overweight. We must quantify and surface uncertainty bands before using these histories in user-facing projections."

- "This forecast method appears to work on historical data because it leaks future information through look-ahead bias. If adopted directly, it would repeatedly recommend overconfident withdrawal strategies that would underperform in live conditions."

If the research touches on user money, health, legal exposure, policy compliance, or other serious stakes, this section is mandatory. Describe what protections or disclosures are needed if we ship the outcome of this research.

## Outcomes & Retrospective

When a major branching point of the research concludes — not just "the end of all research forever," but any significant chapter, such as "we settled on the backfill method and proved it is safe enough for simulator input" — write a retrospective entry here.

This retrospective should include:

1. What we set out to learn.
2. What we actually learned.
3. Which approaches failed and why.
4. Which approach (if any) was promoted to recommended practice.
5. What remains risky or unknown.
6. What should happen next, concretely (for example, "hand off to productionization plan," or "schedule 1 more experiment before rollout").

Think of this as the executive summary for future you six months from now.

## Skeleton of a Good ExecResearch

Below is a template for an ExecResearch document. When generating a new ExecResearch for a specific research question, populate each section in full. Do not delete sections. If a section does not apply, explicitly say "Not applicable and why."

```md
# <Concise, problem-focused title>

This ExecResearch is a living document. It must be kept up to date as experiments are run, results are gathered, and decisions are made. Anyone picking up this file must be able to reproduce prior work, continue running planned experiments, and understand why certain paths were adopted or abandoned.

## Problem Framing & Research Goal

Explain the real-world question we are trying to answer, why it matters to the product, how success will be observed, and what "done" looks like in behavioral terms.

## Prior Art & Background

Describe approaches we already use or know about. For each one:
- What it is, in plain English.
- Whether it solves our problem.
- Whether we've tested it.
- Why it might succeed or fail in our environment.

Call out any constraints specific to our system (data cadence, regulatory exposure, etc.).

## Research Plan & Experiment Design

Lay out the hypotheses we want to test, and for each hypothesis:
- The experiment we will run.
- The dataset(s) and preparation steps.
- The evaluation metrics and acceptance criteria.
- How we will prevent data leakage or self-deception.
- The sequence in which we will run these experiments and why.

Also define any "spike" experiments meant to cheaply de-risk ambitious ideas.

## Progress & Experiment Log

Use a chronological checklist. Every experiment you run or plan goes here.

- [x] (2025-11-07 16:20Z) EXP-01-baseline-synthetic-backfill
      Goal: ...
      Data: ...
      Method: ...
      Result:
          ...
      Interpretation: ...
      Reproduce:
          From repo root, run:
              python path/to/script.py --arg1 ... --seed 42
          Expect:
              <short summarized output>

- [ ] EXP-02-shock-injection
      Planned. Goal: ...
      Acceptance: ...

This section MUST remain current.

## Surprises & Discoveries

List unexpected behaviors with evidence and impact. For each:
- Observation:
- Evidence:
- Impact:

## Decision Log

For every significant decision:
- Decision:
- Rationale:
- Date/Author:
- Evidence reference:

## Interim Conclusions & Recommendations

State which approach currently looks most promising, what blockers remain, and what must happen next. If nothing is promising, say that plainly and describe what line of inquiry should be stopped.

## Reproducibility & Environment Assumptions

Document how to recreate every experiment:
- Runtime environment (language versions, critical libraries, hardware).
- Determinism (seed strategy, split strategy, acceptable tolerance).
- Canonical command(s) to run and where outputs are stored.

## Risk, Ethics, and User Impact

Describe how this work could mislead or harm users if integrated naively, and what protections or disclosures are required.

## Outcomes & Retrospective

At major checkpoints or completion, summarize:
1. What we set out to learn.
2. What we learned.
3. Which methods failed and why.
4. Which method we recommend and why.
5. What remains unknown or risky.
6. What should happen next (for example, productionization plan, follow-up research).

Also append a short note whenever you materially revise this document explaining:
- What changed.
- Why it changed.
- When it changed.
- Who changed it.

