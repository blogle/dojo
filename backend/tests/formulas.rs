use dojo_backend::domain::{Account, Budget, Category, CategoryTransfer, Transaction};
use uuid::Uuid;

#[test]
fn category_and_account_balance() {
    let available_id = Uuid::new_v4();
    let account_id = Uuid::new_v4();
    let cat_id = Uuid::new_v4();

    let mut budget = Budget::default();
    budget.system_available_category_id = available_id;
    budget.accounts.push(Account { id: account_id, name: "Checking".into(), starting_balance: 100.0 });
    budget.categories.push(Category { id: available_id, name: "Available".into() });
    budget.categories.push(Category { id: cat_id, name: "Groceries".into() });

    budget.transactions.push(Transaction {
        id: Uuid::new_v4(),
        date: "2025-06-20".into(),
        payee: None,
        memo: None,
        account_id,
        category_id: Some(cat_id),
        inflow: 0.0,
        outflow: 20.0,
        status: "settled".into(),
    });

    budget.category_transfers.push(CategoryTransfer {
        id: Uuid::new_v4(),
        date: "2025-06-20".into(),
        from_category_id: available_id,
        to_category_id: cat_id,
        amount: 50.0,
        memo: None,
    });

    assert_eq!(budget.category_balance(cat_id), 30.0);
    assert_eq!(budget.account_balance(account_id), 80.0);
    // after transfer 50 to cat_id, available decreases
    assert_eq!(budget.available_to_budget(), -50.0);
}
