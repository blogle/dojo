# Contributing

We welcome contributions to Dojo! Thank you for your interest in improving the project.

## Getting Started

Before you begin, please ensure you have the development environment set up as described in the main `README.md`.

## Guidelines

All code and documentation contributions must adhere to the standards and principles outlined in our project documentation. Before submitting a pull request, please review the following guides:

- **[Engineering Guide](./docs/rules/engineering_guide.md)**: Core backend logic and data model implementation.
- **[Python Style Guide](./docs/rules/python.md)**: Python best practices, naming, and style.
- **[SQL Best Practices](./docs/rules/sql.md)**: Standards for writing and organizing SQL.
- **[Financial Math Rulebook](./docs/rules/fin_math.md)**: Practices for financial calculations.

### End-to-End Testing

Our end-to-end (E2E) tests are critical for validating user workflows and preventing regressions. Please adhere to the following guidelines when contributing E2E tests:

-   **User-Story Driven**: Each test file in `cypress/e2e/user-stories/` corresponds to a canonical user story defined in `docs/plans/envelope-budget-e2e-mvp.md`.
-   **Atomic & Isolated**: Every test (`it` block) must be completely independent. The database is reset and seeded with a specific SQL fixture (from `tests/fixtures/`) in a `beforeEach()` hook to ensure a pristine and predictable state for each test.
-   **Page Objects**: Utilize Page Objects (located in `cypress/support/pages/`) to abstract UI interactions. Tests should describe *what* a user is doing, not *how* to interact with DOM elements.
-   **Resilient Selectors**: Prefer `data-testid` attributes for selecting UI elements over brittle CSS classes or DOM structure.
-   **Network Waiting**: Always wait for network responses when an action triggers a backend call using `cy.intercept().as('alias')` and `cy.wait('@alias')`.

**Running E2E Tests**:
-   To run all E2E tests: `npx cypress run --e2e`
-   To open the Cypress test runner for interactive development: `npx cypress open --e2e --browser chrome --headed`

## Pull Request Process

1.  Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2.  Update the `README.md` with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters.
3.  Increase the version numbers in any examples and the `README.md` to the new version that this Pull Request would represent. The versioning scheme we use is [SemVer](http://semver.org/).
4.  Once your pull request is submitted, the project maintainer will review it. Please ensure your PR adheres to all guidelines in this document to streamline the review process. Approved pull requests will be merged by the maintainer.
