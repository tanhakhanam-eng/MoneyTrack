from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_session_token, hash_password, verify_password
from app.db.base import Base
from app.db.session import engine, get_db
from app.models import Business, BusinessMembership, Customer, Product, User

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_STORE: dict[str, int] = {}
Base.metadata.create_all(bind=engine)


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    business_name: str
    business_type: str = "other"
    preferred_language: str = "en"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProductCreateRequest(BaseModel):
    name: str
    sku: str | None = None
    category: str | None = None
    unit_cost_p: int = 0
    selling_price_p: int = 0
    stock_qty: int = 0
    low_stock_threshold: int = 5
    is_active: bool = True


class CustomerCreateRequest(BaseModel):
    name: str
    phone: str
    address: str | None = None
    notes: str | None = None


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check() -> dict[str, Any]:
    return {"status": "ok", "app": settings.app_name, "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    normalized_email = payload.email.lower().strip()
    existing_user = db.scalars(select(User).where(User.email == normalized_email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    business = Business(
        name=payload.business_name,
        business_type=payload.business_type,
        currency="BDT",
    )
    db.add(business)
    db.flush()

    user = User(
        full_name=payload.full_name,
        email=normalized_email,
        password_hash=hash_password(payload.password),
        preferred_language=payload.preferred_language,
    )
    db.add(user)
    db.flush()

    membership = BusinessMembership(business_id=business.id, user_id=user.id, role="owner")
    db.add(membership)
    db.commit()
    db.refresh(user)
    db.refresh(business)

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "preferred_language": user.preferred_language,
        "business": {
            "id": business.id,
            "name": business.name,
            "business_type": business.business_type,
            "currency": business.currency,
        },
    }


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    normalized_email = payload.email.lower().strip()
    user = db.scalars(select(User).where(User.email == normalized_email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = generate_session_token()
    SESSION_STORE[token] = user.id
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )

    business = db.scalars(
        select(Business).join(BusinessMembership, BusinessMembership.business_id == Business.id).where(
            BusinessMembership.user_id == user.id
        )
    ).first()

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "preferred_language": user.preferred_language,
        "business": {
            "id": business.id if business else None,
            "name": business.name if business else None,
            "business_type": business.business_type if business else None,
            "currency": business.currency if business else None,
        },
    }


@app.post("/api/v1/auth/logout")
def logout(response: Response, session_token: str | None = Cookie(default=None, alias="session_token")) -> dict[str, str]:
    if session_token:
        SESSION_STORE.pop(session_token, None)
    response.delete_cookie("session_token")
    return {"status": "logged_out"}


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias="session_token"),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_id = SESSION_STORE.get(session_token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@app.get("/api/v1/auth/me")
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> dict[str, Any]:
    business = current_user.businesses[0] if current_user.businesses else None
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "preferred_language": current_user.preferred_language,
        "business": {
            "id": business.id if business else None,
            "name": business.name if business else None,
            "currency": business.currency if business else None,
        },
    }


@app.get("/api/v1/dashboard/summary")
def dashboard_summary(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> dict[str, Any]:
    business = current_user.businesses[0] if current_user.businesses else None
    if business is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business not found")

    total_orders = db.query(Product).filter(Product.business_id == business.id).count()
    total_customers = db.query(Customer).filter(Customer.business_id == business.id).count()

    return {
        "business_id": business.id,
        "gross_sales_p": 0,
        "operating_expenses_p": 0,
        "estimated_profit_p": 0,
        "outstanding_due_p": 0,
        "total_products": total_orders,
        "total_customers": total_customers,
    }


@app.get("/api/v1/products")
def list_products(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    business = current_user.businesses[0] if current_user.businesses else None
    if business is None:
        return []

    products = db.query(Product).filter(Product.business_id == business.id).all()
    return [
        {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "category": product.category,
            "unit_cost_p": product.unit_cost_p,
            "selling_price_p": product.selling_price_p,
            "stock_qty": product.stock_qty,
            "low_stock_threshold": product.low_stock_threshold,
            "is_active": product.is_active,
        }
        for product in products
    ]


@app.post("/api/v1/products", status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    business = current_user.businesses[0] if current_user.businesses else None
    if business is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business not found")

    product = Product(
        business_id=business.id,
        name=payload.name,
        sku=payload.sku,
        category=payload.category,
        unit_cost_p=payload.unit_cost_p,
        selling_price_p=payload.selling_price_p,
        stock_qty=payload.stock_qty,
        low_stock_threshold=payload.low_stock_threshold,
        is_active=payload.is_active,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "stock_qty": product.stock_qty,
        "selling_price_p": product.selling_price_p,
    }


@app.get("/api/v1/customers")
def list_customers(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    business = current_user.businesses[0] if current_user.businesses else None
    if business is None:
        return []

    customers = db.query(Customer).filter(Customer.business_id == business.id).all()
    return [
        {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "address": customer.address,
            "notes": customer.notes,
        }
        for customer in customers
    ]


@app.post("/api/v1/customers", status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    business = current_user.businesses[0] if current_user.businesses else None
    if business is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business not found")

    customer = Customer(
        business_id=business.id,
        name=payload.name,
        phone=payload.phone,
        address=payload.address,
        notes=payload.notes,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
    }


@app.get("/api/v1/reports/profit")
def profit_report(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> dict[str, Any]:
    business = current_user.businesses[0] if current_user.businesses else None
    if business is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business not found")

    return {
        "gross_sales_p": 0,
        "discounts_p": 0,
        "net_revenue_p": 0,
        "cogs_p": 0,
        "operating_expenses_p": 0,
        "estimated_operating_profit_p": 0,
        "amount_collected_p": 0,
        "customer_due_p": 0,
    }


@app.get("/api/v1/settings")
def settings_view(current_user: Annotated[User, Depends(get_current_user)]) -> dict[str, Any]:
    business = current_user.businesses[0] if current_user.businesses else None
    return {
        "business_name": business.name if business else "",
        "business_type": business.business_type if business else "other",
        "currency": business.currency if business else "BDT",
        "language": current_user.preferred_language,
    }
