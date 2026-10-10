import uuid
import hashlib

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import UserSession


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login_flow() -> None:
    with TestClient(app) as client:
        email = f"seller-{uuid.uuid4().hex[:8]}@example.com"
        password = "StrongPass!1"

        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Rafi Hasan",
                "email": email,
                "password": password,
                "business_name": "Sweet Crumbs",
                "business_type": "homemade_food",
                "preferred_language": "bn",
            },
        )

        assert register_response.status_code == 201, register_response.text
        body = register_response.json()
        assert body["email"] == email
        assert body["business"]["name"] == "Sweet Crumbs"

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200, login_response.text
        assert "session_token" in login_response.cookies

        me_response = client.get("/api/v1/auth/me")
        assert me_response.status_code == 200, me_response.text
        assert me_response.json()["email"] == email

        dashboard_response = client.get("/api/v1/dashboard/summary")
        assert dashboard_response.status_code == 200
        assert "gross_sales_p" in dashboard_response.json()


def test_dashboard_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 401


def test_session_is_persisted_and_revocable() -> None:
    with TestClient(app) as client:
        email = f"session-{uuid.uuid4().hex[:8]}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Session Seller",
                "email": email,
                "password": "StrongPass!1",
                "business_name": "Session Shop",
            },
        )
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "StrongPass!1"},
        )
        token = login_response.cookies.get("session_token")
        assert token

        db = SessionLocal()
        try:
            stored_session = db.scalars(
                select(UserSession).where(
                    UserSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
                )
            ).first()
            assert stored_session is not None
        finally:
            db.close()

        with TestClient(app) as another_client:
            me_response = another_client.get(
                "/api/v1/auth/me",
                cookies={"session_token": token},
            )
            assert me_response.status_code == 200
            logout_response = another_client.post(
                "/api/v1/auth/logout",
                cookies={"session_token": token},
            )
            assert logout_response.status_code == 200
            revoked_response = another_client.get(
                "/api/v1/auth/me",
                cookies={"session_token": token},
            )
            assert revoked_response.status_code == 401


def test_expense_record_updates_profit_summary() -> None:
    with TestClient(app) as client:
        email = f"seller-{uuid.uuid4().hex[:8]}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Amina Noor",
                "email": email,
                "password": "StrongPass!1",
                "business_name": "Noor Studio",
            },
        )
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "StrongPass!1"},
        )
        assert login_response.status_code == 200

        expense_response = client.post(
            "/api/v1/expenses",
            json={"category": "packaging", "description": "Mailers", "amount_p": 250},
        )
        assert expense_response.status_code == 201, expense_response.text
        assert expense_response.json()["amount_p"] == 250

        summary_response = client.get("/api/v1/dashboard/summary")
        assert summary_response.status_code == 200
        assert summary_response.json()["operating_expenses_p"] == 250
        assert summary_response.json()["estimated_profit_p"] == -250

        invalid_expense = client.post(
            "/api/v1/expenses",
            json={"description": "Invalid", "amount_p": 0},
        )
        assert invalid_expense.status_code == 422


def test_product_customer_order_flow_updates_dashboard() -> None:
    with TestClient(app) as client:
        email = f"seller-{uuid.uuid4().hex[:8]}@example.com"
        password = "StrongPass!1"

        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Nadia Rahman",
                "email": email,
                "password": password,
                "business_name": "Green Basket",
                "business_type": "retail",
                "preferred_language": "bn",
            },
        )

        login_response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_response.status_code == 200

        product_response = client.post(
            "/api/v1/products",
            json={
                "name": "Rice Pack",
                "sku": "RICE-001",
                "category": "groceries",
                "unit_cost_p": 250,
                "selling_price_p": 500,
                "stock_qty": 10,
                "low_stock_threshold": 2,
            },
        )
        assert product_response.status_code == 201, product_response.text
        product_id = product_response.json()["id"]

        customer_response = client.post(
            "/api/v1/customers",
            json={
                "name": "Tahmid Ali",
                "phone": "01700000000",
                "address": "Dhaka",
            },
        )
        assert customer_response.status_code == 201, customer_response.text
        customer_id = customer_response.json()["id"]

        order_response = client.post(
            "/api/v1/orders",
            json={
                "customer_id": customer_id,
                "discount_p": 50,
                "delivery_charge_p": 80,
                "payment_amount_p": 600,
                "payment_method": "cash",
                "items": [{"product_id": product_id, "quantity": 3}],
            },
        )

        assert order_response.status_code == 201, order_response.text
        order_body = order_response.json()
        assert order_body["gross_total_p"] == 1530
        assert order_body["outstanding_due_p"] == 930

        stock_response = client.get("/api/v1/products")
        assert stock_response.status_code == 200
        products = stock_response.json()
        product_entry = next(item for item in products if item["id"] == product_id)
        assert product_entry["stock_qty"] == 7

        summary_response = client.get("/api/v1/dashboard/summary")
        assert summary_response.status_code == 200, summary_response.text
        summary = summary_response.json()
        assert summary["gross_sales_p"] == 1530
        assert summary["estimated_profit_p"] == 780
