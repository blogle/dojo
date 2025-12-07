/// <reference types="cypress" />

import allocationPage from '../../support/pages/AllocationPage';
import budgetPage from '../../support/pages/BudgetPage';

const FIXTURE = 'tests/fixtures/e2e_manual_transaction_lifecycle.sql';
// Fixed date: Nov 15, 2025
const FIXED_NOW = new Date('2025-11-15T12:00:00Z').getTime();

describe('User Story 19 - Allocations Page', () => {
  beforeEach(() => {
    const isoDate = new Date(FIXED_NOW).toISOString();
    cy.on('window:before:load', (win) => {
      win.localStorage.setItem('DOJO_TEST_DATE', isoDate);
    });
    cy.clock(FIXED_NOW);
    cy.resetDatabase();
    cy.seedDatabase(FIXTURE);
  });

  it('allows creating and editing allocations', () => {
    cy.intercept('POST', '/api/budget/allocations').as('createAllocation');
    cy.intercept('PUT', '/api/budget/allocations/*').as('updateAllocation');
    cy.intercept('GET', '/api/budget/allocations*').as('fetchAllocations');
    cy.intercept('GET', '/api/budget/ready-to-assign*').as('fetchReadyToAssign');
    cy.intercept('GET', '/api/budget-categories*').as('fetchBudgetCategories');
    cy.intercept('GET', '/api/reference-data').as('fetchReferenceData');

    allocationPage.visit();
    cy.wait(1000); // Give Vue app time to render
    cy.wait('@fetchAllocations');
    cy.wait('@fetchReadyToAssign');
    cy.wait('@fetchReferenceData');

    allocationPage.verifyMonthInflow('$0.00');
    
    allocationPage.getReadyToAssign().then((initialRTA) => {
      expect(initialRTA).to.be.oneOf([9800, 10000]);
      cy.wrap(initialRTA).as('initialRTA');
    });

    // Create a new allocation from Ready to Assign
    allocationPage.createAllocation(
      '2025-11-15',
      '100',
      null, // From Ready to Assign
      'Dining Out',
      'Initial allocation for dining'
    );
    cy.wait('@createAllocation').its('response.statusCode').should('eq', 201);
    cy.wait('@fetchAllocations');
    cy.wait('@fetchReadyToAssign');

    allocationPage.verifyAllocationRow(0, '2025-11-15', '$100.00', 'Ready to Assign', 'Dining Out', 'Initial allocation for dining');
    allocationPage.verifyMonthInflow('$100.00');
    
    cy.get('@initialRTA').then((initialRTA) => {
        const expected = initialRTA - 100;
        allocationPage.verifyReadyToAssign(`$${expected.toLocaleString('en-US', {minimumFractionDigits: 2})}`);
    });

    // Create another allocation from one category to another
    allocationPage.createAllocation(
      '2025-11-16',
      '50',
      'Dining Out',
      'Groceries',
      'Transfer for groceries'
    );
    cy.wait('@createAllocation').its('response.statusCode').should('eq', 201);
    cy.wait('@fetchAllocations');
    cy.wait('@fetchReadyToAssign');

    allocationPage.verifyAllocationRow(0, '2025-11-16', '$50.00', 'Dining Out', 'Groceries', 'Transfer for groceries');
    allocationPage.verifyMonthInflow('$150.00'); // Still $150 allocated in total for the month
    
    cy.get('@initialRTA').then((initialRTA) => {
        const expected = initialRTA - 100; // Unchanged by cat-to-cat transfer
        allocationPage.verifyReadyToAssign(`$${expected.toLocaleString('en-US', {minimumFractionDigits: 2})}`);
    });

    // Inline edit an allocation
    allocationPage.editAllocation(1); // Edit the first allocation (Dining Out)

    allocationPage.setInlineAmount('120');
    allocationPage.setInlineToCategory('Groceries');
    allocationPage.setInlineMemo('Updated dining allocation');
    allocationPage.saveInlineEdit();

    cy.wait('@updateAllocation').its('response.statusCode').should('eq', 200);
    cy.wait('@fetchAllocations');
    cy.wait('@fetchReadyToAssign');


    allocationPage.verifyAllocationRow(1, '2025-11-15', '$120.00', 'Ready to Assign', 'Groceries', 'Updated dining allocation');
    allocationPage.verifyMonthInflow('$170.00'); // 120 + 50
    
    cy.get('@initialRTA').then((initialRTA) => {
        const expected = initialRTA - 120;
        allocationPage.verifyReadyToAssign(`$${expected.toLocaleString('en-US', {minimumFractionDigits: 2})}`);
    });

    // Test validation for insufficient funds
    allocationPage.createAllocation(
      '2025-11-17',
      '1000',
      null,
      'Groceries',
      'Too much'
    );
    // Should not call API, but show error
    cy.get('@createAllocation').should('not.have.been.called');
    allocationPage.verifyFormError('Not enough Ready to Assign funds.');
  });
});