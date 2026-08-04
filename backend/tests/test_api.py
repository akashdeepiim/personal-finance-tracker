from fastapi.testclient import TestClient

import main
from database import SessionLocal
from models import (
    Analysis,
    CategoryLearning,
    LoginThrottle,
    Statement,
    Transaction,
    User,
    UserSession,
)

SERVICE_HEADERS = {"Authorization": "Bearer test-token"}


def _clear_database():
    with SessionLocal() as session:
        session.query(Transaction).delete()
        session.query(Statement).delete()
        session.query(Analysis).delete()
        session.query(CategoryLearning).delete()
        session.query(UserSession).delete()
        session.query(LoginThrottle).delete()
        session.query(User).delete()
        session.commit()


def _signup(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/signup",
        headers=SERVICE_HEADERS,
        json={"email": email, "password": "a-secure-password-123"},
    )
    assert response.status_code == 201
    return {
        **SERVICE_HEADERS,
        "X-Session-Token": response.json()["token"],
    }


def test_upload_and_currency_scoped_spending(monkeypatch):
    _clear_database()
    monkeypatch.setattr(main, "API_TOKEN", "test-token")
    monkeypatch.setattr(
        main.currency_converter, "rates_cache", {"USD": 1.0, "INR": 80.0}
    )
    monkeypatch.setattr(main.currency_converter, "_is_cache_expired", lambda: False)
    client = TestClient(main.app)
    headers = _signup(client, "owner@example.com")
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


def test_accounts_cannot_read_or_mutate_each_others_data(monkeypatch):
    _clear_database()
    monkeypatch.setattr(main, "API_TOKEN", "test-token")
    monkeypatch.setattr(main.currency_converter, "rates_cache", {"USD": 1.0})
    monkeypatch.setattr(main.currency_converter, "_is_cache_expired", lambda: False)
    client = TestClient(main.app)
    first = _signup(client, "first@example.com")
    second = _signup(client, "second@example.com")
    csv = b"Date,Description,Amount,Currency\n2025-02-01,Coffee Shop,-10.00,USD\n"

    first_upload = client.post(
        "/api/upload-statement",
        headers=first,
        files={"file": ("same.csv", csv, "text/csv")},
        data={"account_type": "bank_account"},
    )
    assert first_upload.status_code == 200
    first_transaction = client.get("/api/transactions", headers=first).json()[0]
    first_statement = first_upload.json()["statement_id"]

    assert client.get("/api/transactions", headers=second).json() == []
    assert client.get("/api/analysis-periods", headers=second).json() == {"periods": []}
    assert (
        client.put(
            f"/api/transactions/{first_transaction['id']}?category=Shopping",
            headers=second,
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/statements/{first_statement}", headers=second).status_code
        == 404
    )

    # Identical files are allowed in different accounts.
    second_upload = client.post(
        "/api/upload-statement",
        headers=second,
        files={"file": ("same.csv", csv, "text/csv")},
        data={"account_type": "bank_account"},
    )
    assert second_upload.status_code == 200
    client.delete("/api/data/clear-all", headers=first)
    assert len(client.get("/api/transactions", headers=second).json()) == 1
    _clear_database()


def test_login_logout_and_validation(monkeypatch):
    _clear_database()
    monkeypatch.setattr(main, "API_TOKEN", "test-token")
    client = TestClient(main.app)
    headers = _signup(client, "Person@Example.COM")
    assert (
        client.get("/api/auth/me", headers=headers).json()["email"]
        == "person@example.com"
    )
    assert (
        client.post(
            "/api/auth/signup",
            headers=SERVICE_HEADERS,
            json={"email": "bad", "password": "short"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/login",
            headers=SERVICE_HEADERS,
            json={"email": "person@example.com", "password": "wrong-password"},
        ).status_code
        == 401
    )
    login = client.post(
        "/api/auth/login",
        headers=SERVICE_HEADERS,
        json={"email": "person@example.com", "password": "a-secure-password-123"},
    )
    assert login.status_code == 200
    login_headers = {**SERVICE_HEADERS, "X-Session-Token": login.json()["token"]}
    assert client.post("/api/auth/logout", headers=login_headers).status_code == 200
    assert client.get("/api/auth/me", headers=login_headers).status_code == 401
    _clear_database()


def test_repeated_failed_logins_are_throttled(monkeypatch):
    _clear_database()
    monkeypatch.setattr(main, "API_TOKEN", "test-token")
    client = TestClient(main.app)
    payload = {"email": "unknown@example.com", "password": "incorrect-password"}
    for _ in range(5):
        assert (
            client.post(
                "/api/auth/login", headers=SERVICE_HEADERS, json=payload
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", headers=SERVICE_HEADERS, json=payload
        ).status_code
        == 429
    )
    _clear_database()
