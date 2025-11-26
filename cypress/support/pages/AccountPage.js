class AccountPage {
    visit() {
        cy.visit("/#/accounts");
    }

    verifyAccountBalance(accountName, expectedBalance) {
        cy.contains(".account-card__name", accountName)
            .parents(".account-card")
            .find(".account-card__balance")
            .should("contain", expectedBalance);
    }

    verifyNetWorth(expectedNetWorth) {
        cy.get("#net-worth").should("have.text", expectedNetWorth);
    }
}

export default new AccountPage();
