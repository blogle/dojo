use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Clone, Serialize, Deserialize)]
pub struct Account {
    pub id: Uuid,
    pub name: String,
    pub starting_balance: f64,
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

pub struct Budget {
    /// Special category holding unallocated funds
    pub system_available_category_id: Uuid,
    pub accounts: Vec<Account>,
    pub categories: Vec<Category>,
    pub transactions: Vec<Transaction>,
    pub category_transfers: Vec<CategoryTransfer>,
    pub account_transfers: Vec<AccountTransfer>,
}

impl Default for Budget {
    fn default() -> Self {
        Self {
            system_available_category_id: Uuid::nil(),
            accounts: Vec::new(),
            categories: Vec::new(),
            transactions: Vec::new(),
            category_transfers: Vec::new(),
            account_transfers: Vec::new(),
        }
    }
}

impl Budget {
    pub fn category_balance(&self, cat: Uuid) -> f64 {
        let mut balance = 0.0;
        for tx in self.transactions.iter().filter(|t| t.category_id == Some(cat)) {
            balance += tx.inflow - tx.outflow;
        }
        for tr in &self.category_transfers {
            if tr.to_category_id == cat {
                balance += tr.amount;
            }
            if tr.from_category_id == cat {
                balance -= tr.amount;
            }
        }
        balance
    }

    pub fn available_to_budget(&self) -> f64 {
        self.category_balance(self.system_available_category_id)
    }

    pub fn account_balance(&self, acc: Uuid) -> f64 {
        let starting = self
            .accounts
            .iter()
            .find(|a| a.id == acc)
            .map(|a| a.starting_balance)
            .unwrap_or(0.0);
        let mut balance = starting;
        for tx in self.transactions.iter().filter(|t| t.account_id == acc) {
            balance += tx.inflow - tx.outflow;
        }
        balance
    }
}
