const getLegacyBody = () => {
	return cy.get("body").then(($body) => {
		if ($body.find('iframe[title="Dojo legacy app"]').length) {
			return cy
				.get('iframe[title="Dojo legacy app"]')
				.its("0.contentDocument.body")
				.should("not.be.empty")
				.then(cy.wrap);
		}
		return cy.get("body");
	});
};

class AccountPage {
	visit() {
		cy.visit("/#/accounts");
	}

	verifyAccountBalance(accountName, expectedBalance) {
		getLegacyBody()
			.contains(".account-card__name", accountName)
			.parents(".account-card")
			.find(".account-card__balance")
			.should("contain", expectedBalance);
	}

	verifyNetWorth(expectedNetWorth) {
		getLegacyBody().find("#net-worth").should("have.text", expectedNetWorth);
	}
}

export default new AccountPage();
