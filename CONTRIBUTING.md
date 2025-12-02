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
- **[Cypress Best Practices](./docs/rules/cypress.md)**: Guidelines for writing stable and maintainable E2E tests.

### End-to-End Testing

Our end-to-end (E2E) tests are critical for validating user workflows and preventing regressions. For detailed best practices on writing stable and maintainable E2E tests, including principles for atomicity, Page Objects, resilient selectors, and network waiting, please refer to the **[Cypress Best Practices Guide](./docs/rules/cypress.md)**.

**Running E2E Tests**:
-   To run all E2E tests: `run-tests --filter e2e`
-   To open the Cypress test runner for interactive development: `npx cypress open --e2e --browser chrome`

## Pull Request Process

1.  Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2.  Update the `README.md` with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters.
3.  Increase the version numbers in any examples and the `README.md` to the new version that this Pull Request would represent. The versioning scheme we use is [SemVer](http://semver.org/).
4.  Once your pull request is submitted, the project maintainer will review it. Please ensure your PR adheres to all guidelines in this document to streamline the review process. Approved pull requests will be merged by the maintainer.
