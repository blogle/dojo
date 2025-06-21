use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Clone, Serialize, Deserialize)]
pub struct Account {
    pub id: Uuid,
    pub name: String,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Category {
    pub id: Uuid,
    pub name: String,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub id: Uuid,
    pub date: String,
    pub payee: Option<String>,
    pub memo: Option<String>,
    pub account_id: Uuid,
    pub category_id: Option<Uuid>,
    pub inflow: f64,
    pub outflow: f64,
    pub status: String,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct CategoryTransfer {
    pub id: Uuid,
    pub date: String,
    pub from_category_id: Uuid,
    pub to_category_id: Uuid,
    pub amount: f64,
    pub memo: Option<String>,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct AccountTransfer {
    pub id: Uuid,
    pub date: String,
    pub from_account_id: Uuid,
    pub to_account_id: Uuid,
    pub amount: f64,
    pub memo: Option<String>,
}

#[derive(Default)]
pub struct Budget {
    pub accounts: Vec<Account>,
    pub categories: Vec<Category>,
    pub transactions: Vec<Transaction>,
    pub category_transfers: Vec<CategoryTransfer>,
    pub account_transfers: Vec<AccountTransfer>,
}
