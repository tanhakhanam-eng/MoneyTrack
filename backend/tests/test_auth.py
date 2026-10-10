import uuid

from fastapi.testclient import TestClient

from app.main import app


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
