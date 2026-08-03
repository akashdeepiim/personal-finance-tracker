from fastapi.testclient import TestClient

import main
from database import SessionLocal
from models import Analysis, CategoryLearning, Statement, Transaction


def _clear_database():
    with SessionLocal() as session:
        session.query(Transaction).delete()
        session.query(Statement).delete()
        session.query(Analysis).delete()
        session.query(CategoryLearning).delete()
        session.commit()


def test_upload_and_currency_scoped_spending(monkeypatch):
    _clear_database()
    monkeypatch.setattr(main, "API_TOKEN", "test-token")
    monkeypatch.setattr(
        main.currency_converter, "rates_cache", {"USD": 1.0, "INR": 80.0}
    )
    monkeypatch.setattr(main.currency_converter, "_is_cache_expired", lambda: False)
    client = TestClient(main.app)
    headers = {"Authorization": "Bearer test-token"}
    csv = b"Date,Description,Debit,Credit,Currency\n2024-01-02,Coffee Shop,12.50,,USD\n2024-01-03,Salary,,100.00,USD\n"

    upload = client.post(
        "/api/upload-statement",
        headers=headers,
        files={"file": ("bank.csv", csv, "text/csv")},
        data={"account_type": "bank_account"},
    )
    assert upload.status_code == 200
    assert upload.json()["transactions_count"] == 2
    duplicate = client.post(
        "/api/upload-statement",
        headers=headers,
        files={"file": ("bank.csv", csv, "text/csv")},
        data={"account_type": "bank_account"},
    )
    assert duplicate.status_code == 409

    trends = client.get("/api/trends?currency=INR", headers=headers)
    assert trends.json()["trends"] == [
        {
            "month": "2024-01",
            "total": 1000.0,
            "income": 8000.0,
            "refunds": 0,
            "net_cash_flow": 7000.0,
        }
    ]

    periods = client.get("/api/analysis-periods", headers=headers)
    assert periods.json() == {
        "periods": [{"year": 2024, "month": 1, "transaction_count": 2}]
    }

    categories = client.get(
        "/api/categories?month=1&year=2024&currency=INR", headers=headers
    )
    assert categories.json()["total"] == 1000.0

    transactions = client.get(
        "/api/transactions?month=1&year=2024", headers=headers
    ).json()
    transaction_id = next(
        item["id"] for item in transactions if item["transaction_type"] == "debit"
    )
    update = client.put(
        f"/api/transactions/{transaction_id}?category=Shopping", headers=headers
    )
    assert update.status_code == 200
    assert update.json()["matching_updated"] == 0
    analysis = client.get("/api/analysis/2024/1?currency=INR", headers=headers)
    assert "Shopping" in analysis.json()["category_breakdown"]

    cleared = client.delete("/api/data/clear-all", headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["deleted_learning_rules"] == 1
    _clear_database()
