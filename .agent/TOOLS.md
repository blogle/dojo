# Generate Tool (GenTool): Repository Development Scripts (Wrapper Commands for Agents & Humans)

You are an autonomous coding agent working inside a repository that uses a `scripts/` directory to expose **project-specific wrapper commands** for development tasks (linters, tests, migrations, orchestration, cleanup, etc.). Your job is to **design, implement, and maintain** these scripts and their documentation so that both humans and other agents can reliably use them without confusion or noisy output.

This meta-prompt defines how you should:
- Create and update scripts in `scripts/`
- Implement a catalog `scripts/README.md`
- Integrate these scripts into `AGENTS.md`
- Enforce the **“thin wrapper, rich behavior”** pattern:
  - Correct tool invocation and arguments
  - Terse, LLM-friendly summaries
  - Progressive disclosure of detailed logs via temp files


## Core Goals

1. **Single source of truth for dev commands**  
   All routine dev tasks (linting, tests, migrations, data cleanup, dev servers, etc.) should be runnable via opinionated wrapper scripts in `scripts/`.

2. **LLM-friendly behavior**  
   Scripts must:
   - **Hide noisy logs on success**; print only short, structured summaries.
   - On failure, **summarize plus point to a temp log file** containing full details.
   - Use **clear exit codes**: `0` for success, non-zero for failure.

3. **Progressive disclosure of context**  
   - If everything passes, only a small number of summary lines should be printed (think `pytest`-style output).
   - If something fails, print:
     - A concise summary of which suite/tool failed.
     - A path to a temp file with the full logs.
   - This avoids overflowing an LLM message while allowing follow-up calls to `cat`, `tail`, or `grep` the temp file when deeper debugging is needed.

4. **Documentation & discoverability**  
   - Maintain a `scripts/README.md` that catalogs all scripts, their purpose, and usage examples.
   - Update `AGENTS.md` to explicitly instruct agents to use scripts in `scripts/` instead of raw tools (e.g., `scripts/lint` instead of `ruff`, `eslint`, `sqlfluff` directly).


## Repository Conventions & Pre-Work

Before creating or modifying anything:

1. **Scan for existing conventions**  
   - Read, if present:
     - `AGENTS.md`
     - Any language/style guides (e.g., `PYTHON_BEST_PRACTICES.md`, `CONTRIBUTING.md`, `PLANS.md`, `ExecPlan` docs).
   - Respect existing rules about:
     - import style
     - code layout
     - tooling choices
     - directory structure

2. **Respect existing behavior**  
   - If `scripts/` already exists, do not break expected behavior of existing scripts without:
     - clearly documenting the change in `scripts/README.md`, and
     - preserving backward compatibility where reasonable (e.g., same script name and basic flags).

3. **Default assumptions (if nothing exists yet)**  
   - Create `scripts/` at the repo root.
   - Default to **POSIX-compatible shell** or `bash` for wrappers unless the repo clearly prefers another language (Python, Node, etc.).
   - Keep scripts **small and focused**; do not embed large logic inline if it is better placed in existing application code.


## Script Design Pattern

For every script you create or maintain in `scripts/`:

### 1. Location & Naming

- Place the file in `scripts/`.
- Use short, verb-like names that describe the action:
  - `scripts/lint`
  - `scripts/test`
  - `scripts/test-e2e`
  - `scripts/migrate`
  - `scripts/dev-server`
- Avoid deep subdirectories unless the repo has a strong, existing convention.

### 2. Shebang & Executability

- Every script must:
  - Start with an appropriate shebang, e.g.:

        #!/usr/bin/env bash

    or (if more appropriate):

        #!/usr/bin/env python3

  - Be marked executable (e.g., `chmod +x scripts/lint`).

### 3. Header Documentation (Manpage-style)

- Immediately after the shebang, include a short, **comment-based manpage header** with at least:

    - NAME
    - SYNOPSIS (usage line)
    - DESCRIPTION

  Example structure:

    # NAME
    #     lint - run all project linters with repo-standard settings
    # SYNOPSIS
    #     scripts/lint [--all] [--fix]
    # DESCRIPTION
    #     Runs ruff, sqlfluff, and eslint with the correct arguments for this repo.
    #     Prints a terse summary on success, and log locations on failure.

- Ensure each script also supports `-h`/`--help` to print a usable help message derived from this header.

### 4. Behavior for Linters (Example: ruff, sqlfluff, eslint)

Implement linter scripts (e.g., `scripts/lint`) according to:

- Run the linters in a deterministic order (e.g. ruff → sqlfluff → eslint) with **repo-specific arguments** baked in.
- On **full success**:
  - Print a single, concise line that includes:
    - Status (OK)
    - Script name or suite(s)
    - Tools involved
    - Elapsed time
  - Example:

        [OK] lint (ruff, sqlfluff, eslint) in 3.2s

- On **failure**:
  - For each tool that fails:
    - Capture its full output to a temp file.
    - Print a short line pointing to that file, plus a brief summary of the error context if easily extractable.
  - Example:

        [FAIL] lint: ruff failed in 0.9s (log: /tmp/repo-lint-ruff-abc123.log)
        [OK]   lint: sqlfluff in 1.1s
        [OK]   lint: eslint in 2.4s

- Return **non-zero** exit code if any tool fails.

### 5. Behavior for Tests (Unit, Property, Integration, E2E, etc.)

For test scripts (e.g., `scripts/test`, `scripts/test-e2e`, `scripts/test-all`):

- Group tests into **logical suites**:
  - unit
  - property
  - integration
  - e2e (e.g., Cypress, Playwright)
- For each suite:
  - Time the execution.
  - Capture full stdout/stderr to a temp file.
- On **suite success**:
  - Print a single summary line, no verbose logs:
    
        [OK]   unit tests in 1.4s
        [OK]   property tests in 0.8s
        [OK]   integration tests in 3.1s
        [OK]   e2e tests (cypress) in 14.6s

- On **suite failure**:
  - Print a concise failure line including:
    - Suite name
    - Elapsed time
    - Temp log path
  - Example:

        [FAIL] e2e tests (cypress) in 23.7s (log: /tmp/repo-e2e-cypress-xyz789.log)

  - Optionally print a short tail of the log (e.g., last 20–50 lines) to give immediate context without overwhelming output.
- Total script exit code should be non-zero if any suite fails.

### 6. Temp File Management

- Use an OS temp directory (e.g. `mktemp`) or a clearly segregated temp path.
- Preferred naming pattern:

    - `/tmp/<repo>-<script>-<tool-or-suite>-<random>.log`

- Do **not** commit temp logs to the repo.
- Ensure paths are:
  - Plain text
  - Standalone (no shell control characters)
  - Easy to copy into a `cat`, `tail`, or `grep` command.

### 7. Output Format & Elapsed Time

- All summary lines should follow a consistent pattern so they are easy for agents to parse:

    - `[OK] <label> in <seconds>s`
    - `[FAIL] <label> in <seconds>s (log: <path>)`

- Use a simple timing mechanism appropriate to the script language:
  - In shell: record start time and end time using a high-resolution clock if available.
  - In Python: `time.perf_counter()`.

### 8. Exit Codes & Error Handling

- If all underlying tools/suites succeed → exit `0`.
- If any fail → exit **non-zero**.
- Handle common errors gracefully (e.g., missing underlying tools) by:
  - Printing a clear, short message describing what’s missing.
  - Exiting with a failure code.


## `scripts/README.md` Requirements

You must maintain `scripts/README.md` as the **single catalog** of dev scripts.

### 1. Purpose

- Top section briefly describes:

  - The role of `scripts/` (wrapper commands).
  - Why agents and humans should use these scripts instead of calling tools directly.
  - The principles: terse output, progressive disclosure, temp logs, consistent exit codes.

### 2. Script Catalog Structure

For each script in `scripts/`:

- Add or update an entry containing:

  - Script name (e.g., `scripts/lint`)
  - Short description (1–2 sentences)
  - Underlying tools/suites it orchestrates
  - Typical use cases
  - One or more **usage examples**, e.g.:

        Example:
            scripts/lint
            scripts/lint --fix
            scripts/test-e2e --headless

- Keep entries sorted or grouped logically (e.g., by category: linting, tests, db, servers, maintenance).

### 3. Notes for Agents

- Include a small section explicitly targeted at AI agents, e.g.:

  - “Agents: When asked to run linters, always call `scripts/lint` instead of invoking `ruff`, `sqlfluff`, or `eslint` directly.”
  - “Agents: When tests fail, prefer to read the temp log referenced in the `[FAIL]` line rather than rerunning noisy underlying commands.”

- This section should list the most important scripts for agents, such as:
  - `scripts/lint`
  - `scripts/test` / `scripts/test-all`
  - `scripts/test-e2e`
  - `scripts/migrate`
  - `scripts/dev-server`
  - Any other project-critical orchestration scripts.


## `AGENTS.md` Integration

You must update `AGENTS.md` so that all coding agents are aware of the `scripts/` directory.

### 1. Add a “Scripts and Tooling” Section (or Update Existing)

- Clearly state:

  - That `scripts/` is the **canonical interface** for running linters, tests, migrations, etc.
  - Agents **must prefer** calling these scripts instead of raw underlying commands.
  - The expectation of **terse output** and **temp log files** on failures.

- Provide a short table or bullet list mapping tasks to scripts, for example:

    - Linting → `scripts/lint`
    - Unit tests → `scripts/test unit` or `scripts/test` (if single entry point)
    - E2E tests → `scripts/test-e2e`
    - DB migrations → `scripts/migrate`
    - Dev server orchestration → `scripts/dev-server`

### 2. Guidance for Failure Handling

- Instruct agents on how to respond when scripts fail:

  - Do **not** immediately re-run underlying tools directly.
  - Instead:
    - Read the referenced temp log (e.g., via `tail` or `cat`).
    - Extract the relevant error snippet.
    - Use that to guide the fix.
  - Only re-run the script once a fix has been applied.

### 3. Guidance for Maintenance

- Mention that when adding or modifying scripts, agents must:
  - Update `scripts/README.md`.
  - Ensure the new/changed script adheres to the summary/log/exit-code conventions.


## Implementation Steps for the Agent

When this meta-prompt is given, follow this high-level procedure:

1. **Survey**  
   - Inspect current `scripts/`, `AGENTS.md`, and any style guides.
   - Identify existing scripts that should be brought under this pattern.
   - Identify the key dev tasks that currently lack wrappers (e.g., raw `pytest`, `cypress`, `ruff` calls in docs or CI configs).

2. **Design script set**  
   - Decide on the canonical scripts to add or standardize (e.g., `scripts/lint`, `scripts/test`, `scripts/test-e2e`).
   - Define for each script:
     - What underlying tools it runs.
     - How it groups suites.
     - The expected command-line interface (flags, options).

3. **Implement / Refactor scripts**  
   - Create or update scripts in `scripts/` using:
     - Shebang + manpage header
     - Terse summary outputs
     - Temp log capture on failure
     - Exit codes as specified
   - Confirm they are executable.

4. **Update `scripts/README.md`**  
   - Document each script according to the catalog requirements.
   - Add usage examples that reflect realistic workflows.

5. **Update `AGENTS.md`**  
   - Add or revise the “Scripts and Tooling” section to:
     - Direct agents to use scripts.
     - Describe expected script output patterns.
     - Explain how to use temp logs for deeper investigation.

6. **Sanity-check behavior (conceptually or by running)**  
   - Ensure that:
     - Running `scripts/lint` with a clean codebase prints only a couple of short lines.
     - Running `scripts/test` on a passing test suite prints short per-suite summaries.
     - When underlying tools fail, the output:
       - Is still compact.
       - Includes log file paths.
       - Uses consistent `[OK]` / `[FAIL]` formatting.

7. **Summarize your changes**  
   - After implementing, produce a concise summary for the user/maintainer:
     - List scripts created/updated.
     - Briefly describe their purpose and main flags.
     - Mention how `scripts/README.md` and `AGENTS.md` were updated.


## Applicability Beyond Linters & Tests

This pattern applies generically to **any** repo-specific dev script. For example:

- **Migrations** (`scripts/migrate`):
  - Summarize applied migrations.
  - On failure, temp log path and error hint.

- **Process cleanup** (`scripts/cleanup`):
  - Summarize resources cleaned.
  - On failure, log with commands attempted.

- **Orchestration** (`scripts/dev-server`, `scripts/stack-up`):
  - Summarize services started and their health checks.
  - On failure, temp logs from underlying processes.

For every new script you add or modify, conform to the same:
- Manpage header
- Terse summary
- Temp-log on failure
- Clear exit codes
- Documentation in `scripts/README.md`
- Agent guidance in `AGENTS.md` where relevant

