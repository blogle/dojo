use axum::{routing::{get, post}, Router, Extension, Json};
use std::{sync::{Arc, Mutex}};
use tokio::net::TcpListener;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod domain;
use domain::{
    Account, AccountTransfer, Budget, Category, CategoryTransfer, Transaction,
};

#[tokio::main]
async fn main() {
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::from_default_env())
        .with(tracing_subscriber::fmt::layer())
        .init();

    let state = Arc::new(Mutex::new(Budget::default()));

    let app = Router::new()
        .route("/healthz", get(|| async { "ok" }))
        .route("/accounts", post(create_account))
        .route("/accounts", get(list_accounts))
        .route("/categories", post(create_category))
        .route("/categories", get(list_categories))
        .route("/transactions", post(create_transaction))
        .route("/transactions", get(list_transactions))
        .route("/category-transfers", post(create_category_transfer))
        .route("/category-transfers", get(list_category_transfers))
        .route("/account-transfers", post(create_account_transfer))
        .route("/account-transfers", get(list_account_transfers))
        .layer(Extension(state));

    let listener = TcpListener::bind("0.0.0.0:3000").await.unwrap();
    tracing::info!("listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app).await.unwrap();
}

async fn create_account(
    Extension(state): Extension<Arc<Mutex<Budget>>>,
    Json(payload): Json<Account>,
) {
    let mut budget = state.lock().unwrap();
    budget.accounts.push(payload);
}

async fn list_accounts(Extension(state): Extension<Arc<Mutex<Budget>>>) -> Json<Vec<Account>> {
    let budget = state.lock().unwrap();
    Json(budget.accounts.clone())
}

async fn create_category(
    Extension(state): Extension<Arc<Mutex<Budget>>>,
    Json(payload): Json<Category>,
) {
    let mut budget = state.lock().unwrap();
    budget.categories.push(payload);
}

async fn list_categories(Extension(state): Extension<Arc<Mutex<Budget>>>) -> Json<Vec<Category>> {
    let budget = state.lock().unwrap();
    Json(budget.categories.clone())
}

async fn create_transaction(
    Extension(state): Extension<Arc<Mutex<Budget>>>,
    Json(payload): Json<Transaction>,
) {
    let mut budget = state.lock().unwrap();
    budget.transactions.push(payload);
}

async fn list_transactions(
    Extension(state): Extension<Arc<Mutex<Budget>>>,
) -> Json<Vec<Transaction>> {
    let budget = state.lock().unwrap();
    Json(budget.transactions.clone())
}

async fn create_category_transfer(
    Extension(state): Extension<Arc<Mutex<Budget>>>,
    Json(payload): Json<CategoryTransfer>,
) {
    let mut budget = state.lock().unwrap();
    budget.category_transfers.push(payload);
}

async fn list_category_transfers(
    Extension(state): Extension<Arc<Mutex<Budget>>>,
) -> Json<Vec<CategoryTransfer>> {
    let budget = state.lock().unwrap();
    Json(budget.category_transfers.clone())
}

async fn create_account_transfer(
    Extension(state): Extension<Arc<Mutex<Budget>>>,
    Json(payload): Json<AccountTransfer>,
) {
    let mut budget = state.lock().unwrap();
    budget.account_transfers.push(payload);
}

async fn list_account_transfers(
    Extension(state): Extension<Arc<Mutex<Budget>>>,
) -> Json<Vec<AccountTransfer>> {
    let budget = state.lock().unwrap();
    Json(budget.account_transfers.clone())
}
