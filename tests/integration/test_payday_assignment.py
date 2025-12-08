import pytest
from fastapi.testclient import TestClient
from datetime import date
from dojo.core.app import create_app
from dojo.core.config import Settings
from dojo.core.db import connection_dep

@pytest.fixture
def client(in_memory_db):
    settings = Settings(
        db_path=":memory:", 
        run_startup_migrations=False,
        testing=True
    )
    app = create_app(settings)
    
    def override_db():
        yield in_memory_db

    app.dependency_overrides[connection_dep] = override_db
    
    with TestClient(app) as c:
        yield c

def test_payday_assignment_flow(client):
    """
    Integration test for User Story 01: Payday Assignment.
    Verifies that recording an inflow increases Ready to Assign,
    and allocating funds decreases it.
    """
    
    # 0. Check initial Ready to Assign
    response = client.get("/api/budget/ready-to-assign")
    assert response.status_code == 200
    initial_rta = response.json()["ready_to_assign_minor"]

    # 1. Check initial state
    response = client.get("/api/accounts")
    assert response.status_code == 200
    accounts = response.json()
    checking = next((a for a in accounts if a["account_id"] == "house_checking"), None)
    assert checking is not None
    
    # 2. Record Paycheck (Inflow)
    payload = {
        "transaction_date": date.today().isoformat(),
        "account_id": "house_checking",
        "category_id": "available_to_budget",
        "amount_minor": 300000, # $3000.00
        "memo": "Paycheck",
    }
    
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 201
    
    # 3. Check Ready to Assign
    response = client.get("/api/budget/ready-to-assign")
    assert response.status_code == 200
    rta = response.json()["ready_to_assign_minor"]
    
    assert rta == initial_rta + 300000 
    
    # 4. Allocate to Housing
    alloc_payload = {
        "to_category_id": "housing",
        "amount_minor": 150000, # $1500.00
        "month_start": date.today().replace(day=1).isoformat()
    }
    response = client.post("/api/budget/allocations", json=alloc_payload)
    assert response.status_code == 201
    
    # 5. Check Ready to Assign decreased
    response = client.get("/api/budget/ready-to-assign")
    rta_after_alloc = response.json()["ready_to_assign_minor"]
    assert rta_after_alloc == rta - 150000

    # 6. Verify Housing category available amount
    response = client.get("/api/budget-categories")
    categories = response.json()
    housing = next(c for c in categories if c["category_id"] == "housing")
    assert housing["available_minor"] == 150000
