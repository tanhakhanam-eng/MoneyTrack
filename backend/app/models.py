from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_type: Mapped[str] = mapped_column(String(100), default="other")
    currency: Mapped[str] = mapped_column(String(10), default="BDT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="businesses", secondary="business_members")
    products: Mapped[list["Product"]] = relationship(back_populates="business")
    customers: Mapped[list["Customer"]] = relationship(back_populates="business")
    orders: Mapped[list["Order"]] = relationship(back_populates="business")
    payments: Mapped[list["Payment"]] = relationship(back_populates="business")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="business")
    cashbook_entries: Mapped[list["CashbookEntry"]] = relationship(back_populates="business")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(20), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    businesses: Mapped[list[Business]] = relationship(back_populates="users", secondary="business_members", overlaps="memberships")
    memberships: Mapped[list["BusinessMembership"]] = relationship(back_populates="user", overlaps="businesses,users")


class BusinessMembership(Base):
    __tablename__ = "business_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="memberships", overlaps="businesses,users")
    business: Mapped[Business] = relationship(overlaps="businesses,users")

    __table_args__ = (UniqueConstraint("business_id", "user_id", name="uq_business_member"),)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    unit_cost_p: Mapped[int] = mapped_column(Integer, default=0)
    selling_price_p: Mapped[int] = mapped_column(Integer, default=0)
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    business: Mapped[Business] = relationship(back_populates="products")

    __table_args__ = (UniqueConstraint("business_id", "sku", name="uq_business_sku"),)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    business: Mapped[Business] = relationship(back_populates="customers")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")


class Order(Base):
    __tablename__ = "customer_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    order_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    discount_p: Mapped[int] = mapped_column(Integer, default=0)
    delivery_charge_p: Mapped[int] = mapped_column(Integer, default=0)
    delivery_paid_by: Mapped[str] = mapped_column(String(30), default="customer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business: Mapped[Business] = relationship(back_populates="orders")
    customer: Mapped[Customer] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("customer_orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_p: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost_p: Mapped[int] = mapped_column(Integer, default=0)
    line_discount_p: Mapped[int] = mapped_column(Integer, default=0)

    order: Mapped[Order] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("customer_orders.id"), nullable=False)
    amount_p: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str] = mapped_column(String(50), default="cash")
    status: Mapped[str] = mapped_column(String(30), default="received")
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reference: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    business: Mapped[Business] = relationship(back_populates="payments")
    order: Mapped[Order] = relationship(back_populates="payments")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), default="other")
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_p: Mapped[int] = mapped_column(Integer, default=0)
    expense_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    payment_method: Mapped[str] = mapped_column(String(50), default="cash")

    business: Mapped[Business] = relationship(back_populates="expenses")


class CashbookEntry(Base):
    __tablename__ = "cashbook_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customer_orders.id"), nullable=True)
    entry_type: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="other")
    amount_p: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str] = mapped_column(String(50), default="cash")
    entry_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    business: Mapped[Business] = relationship(back_populates="cashbook_entries")
