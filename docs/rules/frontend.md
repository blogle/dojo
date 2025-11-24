# Frontend Development Guide

This guide establishes the standards and best practices for developing the frontend of our application. It prioritizes performance, maintainability, and a clean, stateless architecture. Since we do not use a frontend framework, adherence to these principles is critical for project success.

## Guiding Principles

- **Stateless by Default**: Components should be pure functions where possible, receiving data and returning DOM elements. State should be managed explicitly and not tied to individual components.
- **Performance First**: Optimize for a fast user experience. This includes minimizing repaint/reflow, efficient event handling, and optimizing asset loading.
- **Clarity and Readability**: Write code that is easy to understand and maintain. Use modern JavaScript features where they improve clarity.

## Code Organization

- **Domain-Driven Structure**: Organize files by feature or domain, not by file type. Each page/component owns its DOM bindings, styles, and tests. The current layout under `src/dojo/frontend/static/` is the reference implementation:

  ```
  src/dojo/frontend/static/
  ├── index.html
  ├── main.js               # composition root + router registration
  ├── store.js              # shared immutable state container
  ├── services/
  │   ├── api.js           # fetch wrappers
  │   ├── dom.js           # DOM query helpers
  │   └── format.js        # currency + date helpers
  ├── components/
  │   ├── transactions/
  │   ├── accounts/
  │   ├── budgets/
  │   ├── allocations/
  │   └── transfers/
  └── styles/
      ├── base.css
      ├── forms.css
      ├── layout.css
      ├── ledger.css
      └── components/*.css
  ```

- **Component-Based Architecture**: Even without a framework, we will build the UI using a component-based approach. Each component is a self-contained module with its own logic, template, and styles.

## JavaScript Best Practices

- **ES Modules**: Use ES Modules (`import`/`export`) for all JavaScript files.
- **Pure Functions**: Write pure functions whenever possible. Avoid side effects.
- **State Management**:
    - Centralized State: `store.js` is the only writable store. Modules read via `getState()` and update via `setState`/`patchState` helpers imported from the store.
    - Immutable Updates: Never mutate state slices in place—always spread/clone to produce a new tree before notifying subscribers.
    - State Changes: Events bubble up to the page module, which delegates to the store (optionally via helpers exported from `services/state.js`). Bindings react to store subscriptions instead of ad-hoc globals.
- **Asynchronous Code**: Use `async/await` for all asynchronous operations.
- **DOM Manipulation**:
    - **Vanilla JS**: Use standard DOM APIs for all DOM manipulation.
    - **Efficient Updates**: Minimize direct DOM manipulation. Batch updates where possible.
    - **Event Delegation**: Use event delegation to minimize the number of event listeners.
- **Error Handling**: Use `try/catch` blocks for asynchronous operations and any code that might throw an error.

## HTML Best Practices

- **Semantic HTML**: Use semantic HTML5 elements to structure your content.
- **Accessibility**: Follow WCAG guidelines to ensure the application is accessible to all users.

## CSS Best Practices

- **BEM Naming Convention**: Use the Block, Element, Modifier (BEM) naming convention for all CSS classes to avoid naming collisions and improve readability.
- **Component-Scoped Styles**: Each component should have its own CSS file.
- **Flexbox and Grid**: Use Flexbox and CSS Grid for layout.

## Performance

- **Lazy Loading**: Lazy load images and other assets that are not critical for the initial page load.
- **Debouncing and Throttling**: Use debouncing and throttling for event handlers that fire frequently (e.g., `scroll`, `resize`).
- **Minimize Repaint/Reflow**: Avoid changing styles that trigger a repaint or reflow in a loop.

## Testing

- **Unit Tests**: Write unit tests for all business logic and pure functions using a testing framework like Jest or Vitest.
- **E2E Tests**: Write end-to-end tests for critical user flows using a tool like Cypress.

By following these guidelines, we can build a high-performance, maintainable, and scalable frontend without the overhead of a large framework.
