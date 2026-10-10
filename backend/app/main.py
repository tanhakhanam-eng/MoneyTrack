from __future__ import annotations

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_session_token, hash_password, verify_password
from app.db.base import Base
from app.db.session import engine, get_db
from app.models import Business, BusinessMembership, Customer, Expense, Order, OrderItem, Payment, Product, User, UserSession

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class OrderItemRequest(BaseModel):
    product_id: int
    quantity: int = 1
    line_discount_p: int = 0


class OrderCreateRequest(BaseModel):
    customer_id: int
    items: list[OrderItemRequest] = Field(min_length=1)
    discount_p: int = Field(default=0, ge=0)
    delivery_charge_p: int = Field(default=0, ge=0)
    delivery_paid_by: str = "customer"
    payment_amount_p: int = Field(default=0, ge=0)
    payment_method: str = "cash"


class ExpenseCreateRequest(BaseModel):
    category: str = "other"
    description: str = Field(min_length=1, max_length=255)
    amount_p: int = Field(gt=0)
    payment_method: str = "cash"


def get_business_for_user(current_user: User) -> Business | None:
    return current_user.businesses[0] if current_user.businesses else None


def get_order_total(order: Order) -> int:
    line_total = sum(item.unit_price_p * item.quantity for item in order.items)
    return max(line_total + order.delivery_charge_p - order.discount_p, 0)


def get_order_cost(order: Order) -> int:
    return sum(item.unit_cost_p * item.quantity for item in order.items)


def get_order_paid_amount(order: Order) -> int:
    return sum(payment.amount_p for payment in order.payments)


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
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
    )
    db.commit()
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
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias="session_token"),
) -> dict[str, str]:
    if session_token:
        token_hash = hashlib.sha256(session_token.encode()).hexdigest()
        stored_session = db.scalars(select(UserSession).where(UserSession.token_hash == token_hash)).first()
        if stored_session is not None:
            db.delete(stored_session)
            db.commit()
    response.delete_cookie("session_token")
    return {"status": "logged_out"}


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias="session_token"),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token_hash = hashlib.sha256(session_token.encode()).hexdigest()
    stored_session = db.scalars(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.utcnow(),
        )
    ).first()
    if stored_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    user = db.get(User, stored_session.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@app.get("/api/v1/auth/me")
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> dict[str, Any]:
    business = get_business_for_user(current_user)
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
    business = get_business_for_user(current_user)
    if business is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business not found")

    orders = db.query(Order).filter(Order.business_id == business.id).all()
    expenses = db.query(Expense).filter(Expense.business_id == business.id).all()

    gross_sales_p = sum(get_order_total(order) for order in orders)
    total_cogs_p = sum(get_order_cost(order) for order in orders)
    operating_expenses_p = sum(expense.amount_p for expense in expenses)
    outstanding_due_p = sum(
        max(get_order_total(order) - get_order_paid_amount(order), 0) for order in orders
    )

    total_products = db.query(Product).filter(Product.business_id == business.id).count()
    total_customers = db.query(Customer).filter(Customer.business_id == business.id).count()
    total_orders = len(orders)

    estimated_profit_p = gross_sales_p - total_cogs_p - operating_expenses_p

    return {
        "business_id": business.id,
        "gross_sales_p": gross_sales_p,
        "operating_expenses_p": operating_expenses_p,
        "estimated_profit_p": estimated_profit_p,
        "outstanding_due_p": outstanding_due_p,
        "total_orders": total_orders,
        "total_products": total_products,
        "total_customers": total_customers,
    }


@app.get("/api/v1/reports/profit")
def profit_report(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return dashboard_summary(current_user=current_user, db=db)


@app.get("/api/v1/expenses")
def list_expenses(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    business = get_business_for_user(current_user)
    if business is None:
        return []

    expenses = (
        db.query(Expense)
        .filter(Expense.business_id == business.id)
        .order_by(Expense.expense_date.desc())
        .all()
    )
    return [
        {
            "id": expense.id,
            "category": expense.category,
            "description": expense.description,
            "amount_p": expense.amount_p,
            "expense_date": expense.expense_date.isoformat(),
            "payment_method": expense.payment_method,
        }
        for expense in expenses
    ]


@app.post("/api/v1/expenses", status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    business = get_business_for_user(current_user)
    if business is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business not found")

    expense = Expense(
        business_id=business.id,
        category=payload.category,
        description=payload.description.strip(),
        amount_p=payload.amount_p,
        payment_method=payload.payment_method,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return {
        "id": expense.id,
        "category": expense.category,
        "description": expense.description,
        "amount_p": expense.amount_p,
        "expense_date": expense.expense_date.isoformat(),
        "payment_method": expense.payment_method,
    }


@app.get("/api/v1/products")
def list_products(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    business = get_business_for_user(current_user)
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
    business = get_business_for_user(current_user)
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
    business = get_business_for_user(current_user)
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
    business = get_business_for_user(current_user)
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


@app.get("/api/v1/orders")
def list_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    business = get_business_for_user(current_user)
    if business is None:
        return []

    orders = db.query(Order).filter(Order.business_id == business.id).order_by(Order.created_at.desc()).all()
    results: list[dict[str, Any]] = []

    for order in orders:
        paid_amount = get_order_paid_amount(order)
        results.append(
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer_id": order.customer_id,
                "status": order.status,
                "gross_total_p": get_order_total(order),
                "paid_amount_p": paid_amount,
                "outstanding_due_p": max(get_order_total(order) - paid_amount, 0),
                "items": [
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "product_name_snapshot": item.product_name_snapshot,
                        "quantity": item.quantity,
                        "unit_price_p": item.unit_price_p,
                        "unit_cost_p": item.unit_cost_p,
                    }
                    for item in order.items
                ],
            }
        )

    return results


@app.post("/api/v1/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    business = get_business_for_user(current_user)
    if business is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business not found")

    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order requires at least one item")

    customer = db.get(Customer, payload.customer_id)
    if customer is None or customer.business_id != business.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    subtotal = 0
    total_cost = 0
    order_lines: list[tuple[Product, int]] = []

    for line in payload.items:
        product = db.get(Product, line.product_id)
        if product is None or product.business_id != business.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {line.product_id} not found")
        if product.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product {product.name} is inactive")
        if line.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than zero")
        if product.stock_qty < line.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product.name}. Available: {product.stock_qty}",
            )

        subtotal += product.selling_price_p * line.quantity
        total_cost += product.unit_cost_p * line.quantity
        order_lines.append((product, line.quantity))

    gross_total_p = max(subtotal + payload.delivery_charge_p - payload.discount_p, 0)
    paid_amount_p = min(max(payload.payment_amount_p, 0), gross_total_p)
    outstanding_due_p = max(gross_total_p - paid_amount_p, 0)

    order_number = f"HF-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    order = Order(
        business_id=business.id,
        customer_id=customer.id,
        order_number=order_number,
        status="pending",
        discount_p=payload.discount_p,
        delivery_charge_p=payload.delivery_charge_p,
        delivery_paid_by=payload.delivery_paid_by,
    )
    db.add(order)
    db.flush()

    for product, quantity in order_lines:
        product.stock_qty -= quantity
        item = OrderItem(
            business_id=business.id,
            order_id=order.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            quantity=quantity,
            unit_price_p=product.selling_price_p,
            unit_cost_p=product.unit_cost_p,
            line_discount_p=0,
        )
        db.add(item)

    if paid_amount_p > 0:
        payment = Payment(
            business_id=business.id,
            order_id=order.id,
            amount_p=paid_amount_p,
            method=payload.payment_method,
            status="received",
        )
        db.add(payment)

    db.commit()
    db.refresh(order)

    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_id": order.customer_id,
        "gross_total_p": gross_total_p,
        "paid_amount_p": paid_amount_p,
        "outstanding_due_p": outstanding_due_p,
        "profit_estimate_p": gross_total_p - total_cost,
        "items": [
            {
                "product_id": product.id,
                "quantity": quantity,
                "unit_price_p": product.selling_price_p,
                "unit_cost_p": product.unit_cost_p,
            }
            for product, quantity in order_lines
        ],
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
