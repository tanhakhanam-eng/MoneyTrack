"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Banknote,
  Boxes,
  Check,
  ChevronDown,
  CircleHelp,
  Home as HomeIcon,
  LogOut,
  PackagePlus,
  Plus,
  ReceiptText,
  Search,
  ShoppingBag,
  Sparkles,
  Users,
  WalletCards,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Section = "overview" | "orders" | "products" | "customers" | "expenses";
type Business = { id: number | null; name: string | null; currency?: string };
type User = { id: number; full_name: string; email: string; business: Business };
type Product = {
  id: number;
  name: string;
  sku: string | null;
  category: string | null;
  unit_cost_p: number;
  selling_price_p: number;
  stock_qty: number;
  low_stock_threshold: number;
  is_active: boolean;
};
type Customer = { id: number; name: string; phone: string; address: string | null; notes: string | null };
type Order = {
  id: number;
  order_number: string;
  customer_id: number;
  status: string;
  gross_total_p: number;
  paid_amount_p: number;
  outstanding_due_p: number;
  items: { product_name_snapshot: string; quantity: number }[];
};
type Expense = { id: number; category: string; description: string; amount_p: number; expense_date: string; payment_method: string };
type Summary = {
  gross_sales_p: number;
  operating_expenses_p: number;
  estimated_profit_p: number;
  outstanding_due_p: number;
  total_orders: number;
  total_products: number;
  total_customers: number;
};
type OrderLine = { product_id: number; quantity: number };

const navigation: { id: Section; label: string; icon: typeof HomeIcon }[] = [
  { id: "overview", label: "Overview", icon: HomeIcon },
  { id: "orders", label: "Orders", icon: ShoppingBag },
  { id: "products", label: "Products", icon: Boxes },
  { id: "customers", label: "Customers", icon: Users },
  { id: "expenses", label: "Expenses", icon: ReceiptText },
];

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const detail = error?.detail;
    throw new Error(typeof detail === "string" ? detail : "Something went wrong. Please try again.");
  }
  return response.json() as Promise<T>;
}

function money(value: number) {
  return new Intl.NumberFormat("en-BD", { maximumFractionDigits: 0 }).format(value ?? 0);
}

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
}

function Field({ label, children, className = "" }: { label: string; children: ReactNode; className?: string }) {
  return (
    <label className={`field-label ${className}`}>
      <span>{label}</span>
      {children}
    </label>
  );
}

function EmptyState({ title, detail, action, children }: { title: string; detail: string; action?: ReactNode; children?: ReactNode }) {
  return (
    <div className="empty-state">
      <span className="empty-icon"><Sparkles size={18} /></span>
      <h3>{title}</h3>
      <p>{detail}</p>
      {action}
      {children}
    </div>
  );
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [section, setSection] = useState<Section>("overview");
  const [authMode, setAuthMode] = useState<"login" | "register">("register");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);

  async function refreshData() {
    const [nextSummary, nextProducts, nextCustomers, nextOrders, nextExpenses] = await Promise.all([
      request<Summary>("/api/v1/dashboard/summary"),
      request<Product[]>("/api/v1/products"),
      request<Customer[]>("/api/v1/customers"),
      request<Order[]>("/api/v1/orders"),
      request<Expense[]>("/api/v1/expenses"),
    ]);
    setSummary(nextSummary);
    setProducts(nextProducts);
    setCustomers(nextCustomers);
    setOrders(nextOrders);
    setExpenses(nextExpenses);
  }

  useEffect(() => {
    let active = true;
    async function loadSession() {
      try {
        const currentUser = await request<User>("/api/v1/auth/me");
        if (active) {
          setUser(currentUser);
          await refreshData();
        }
      } catch {
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadSession();
    return () => { active = false; };
  }, []);

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      if (authMode === "register") {
        await request("/api/v1/auth/register", {
          method: "POST",
          body: JSON.stringify({
            full_name: values.full_name,
            email: values.email,
            password: values.password,
            business_name: values.business_name,
            business_type: values.business_type || "other",
          }),
        });
      }
      const currentUser = await request<User>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: values.email, password: values.password }),
      });
      setUser(currentUser);
      await refreshData();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not sign in.");
    } finally {
      setBusy(false);
    }
  }

  async function handleLogout() {
    await request("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setSection("overview");
    setNotice("");
  }

  async function submitAction(event: FormEvent<HTMLFormElement>, path: string, success: string, reset?: () => void) {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(true);
    setError("");
    setNotice("");
    const values = Object.fromEntries(new FormData(form).entries());
    try {
      await request(path, { method: "POST", body: JSON.stringify(values) });
      form.reset();
      reset?.();
      await refreshData();
      setNotice(success);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save this record.");
    } finally {
      setBusy(false);
    }
  }

  function exportReport() {
    const rows = [
      ["Metric", "Amount (BDT)"],
      ["Sales", summary?.gross_sales_p ?? 0],
      ["Expenses", summary?.operating_expenses_p ?? 0],
      ["Estimated profit", summary?.estimated_profit_p ?? 0],
      ["Outstanding due", summary?.outstanding_due_p ?? 0],
      [],
      ["Order", "Status", "Total", "Paid", "Due"],
      ...orders.map((order) => [order.order_number, order.status, order.gross_total_p, order.paid_amount_p, order.outstanding_due_p]),
    ];
    const csv = rows.map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "moneytrack-profit-report.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  if (loading) {
    return <main className="loading-screen"><span className="brand-mark"><Banknote size={22} /></span><p>Opening your books...</p></main>;
  }

  if (!user) {
    return (
      <main className="auth-screen">
        <section className="auth-story">
          <div className="auth-topline"><span className="brand-mark"><Banknote size={22} /></span><span>MoneyTrack</span></div>
          <div className="auth-copy">
            <span className="eyebrow"><Sparkles size={14} /> YOUR BUSINESS, IN FOCUS</span>
            <h1>Make every order<br />count toward <em>profit.</em></h1>
            <p>One calm place to keep track of sales, stock, customers, and the money you actually make.</p>
          </div>
          <div className="auth-note"><span className="note-line" /><span>Made for the way small businesses work in Bangladesh.</span></div>
          <div className="auth-art" aria-hidden="true"><div className="art-sun" /><div className="art-card art-card-one"><span>PROFIT SNAPSHOT</span><strong>৳ —</strong><small>Updates as orders come in</small></div><div className="art-card art-card-two"><span className="art-check"><Check size={15} /></span><div><strong>Track every order</strong><small>Stock · payment · profit</small></div><b><ArrowRight size={15} /></b></div><div className="art-ring" /></div>
        </section>
        <section className="auth-panel">
          <form className="auth-form" onSubmit={handleAuth}>
            <div className="auth-heading"><p className="eyebrow">{authMode === "register" ? "GET STARTED" : "WELCOME BACK"}</p><h2>{authMode === "register" ? "Your next chapter starts here." : "Good to see you again."}</h2><p>{authMode === "register" ? "Create your workspace. It only takes a minute." : "Sign in to pick up where you left off."}</p></div>
            {authMode === "register" && <Field label="Your name"><input name="full_name" required placeholder="e.g. Samira Rahman" autoComplete="name" /></Field>}
            {authMode === "register" && <Field label="Business name"><input name="business_name" required placeholder="e.g. Samira's Kitchen" /></Field>}
            <Field label="Email address"><input name="email" type="email" required placeholder="you@example.com" autoComplete="email" /></Field>
            <Field label="Password"><input name="password" type="password" minLength={8} required placeholder="At least 8 characters" autoComplete={authMode === "register" ? "new-password" : "current-password"} /></Field>
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="button button-primary auth-submit" disabled={busy}>{busy ? "Please wait..." : authMode === "register" ? "Create your workspace" : "Sign in"}<ArrowRight size={17} /></button>
            <p className="auth-switch">{authMode === "register" ? "Already have an account?" : "New to MoneyTrack?"}<button type="button" onClick={() => { setAuthMode(authMode === "register" ? "login" : "register"); setError(""); }}>{authMode === "register" ? "Sign in" : "Create an account"}</button></p>
            <p className="auth-security"><CircleHelp size={14} /> Your business data stays private to your account.</p>
          </form>
        </section>
      </main>
    );
  }

  const sectionTitle = navigation.find((item) => item.id === section)?.label ?? "Overview";
  const collected = (summary?.gross_sales_p ?? 0) - (summary?.outstanding_due_p ?? 0);
  const metrics = [
    { label: "Sales recorded", value: summary?.gross_sales_p ?? 0, icon: Banknote, color: "green", caption: `${summary?.total_orders ?? 0} orders so far` },
    { label: "Estimated profit", value: summary?.estimated_profit_p ?? 0, icon: Sparkles, color: "yellow", caption: "After product costs & expenses" },
    { label: "Still to collect", value: summary?.outstanding_due_p ?? 0, icon: WalletCards, color: "coral", caption: `৳${money(collected)} collected` },
    { label: "Operating costs", value: summary?.operating_expenses_p ?? 0, icon: ReceiptText, color: "blue", caption: `${summary?.total_products ?? 0} product${summary?.total_products === 1 ? "" : "s"} tracked` },
  ];

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand-lockup" href="#overview" onClick={(event) => { event.preventDefault(); setSection("overview"); }}><span className="brand-mark"><Banknote size={21} /></span><span>Money<span className="brand-light">Track</span></span></a>
        <div className="workspace-switch"><span className="workspace-avatar">{initials(user.business.name ?? user.full_name)}</span><span className="workspace-text"><strong>{user.business.name ?? "My business"}</strong><small>Business workspace</small></span><ChevronDown size={15} /></div>
        <p className="nav-caption">WORKSPACE</p>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${section === id ? "active" : ""}`} onClick={() => { setSection(id); setError(""); setNotice(""); }}><Icon size={18} strokeWidth={1.8} /><span>{label}</span>{id === "orders" && orders.length > 0 && <small>{orders.length}</small>}</button>)}
        </nav>
        <div className="sidebar-bottom"><div className="help-strip"><span><CircleHelp size={17} /></span><div><strong>Need a hand?</strong><small>We&apos;re here to help.</small></div><ArrowRight size={15} /></div><button className="profile-button" onClick={handleLogout}><span className="profile-avatar">{initials(user.full_name)}</span><span className="profile-info"><strong>{user.full_name}</strong><small>{user.email}</small></span><LogOut size={16} /></button></div>
      </aside>

      <section className="main-column">
        <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><span>/</span><strong>{sectionTitle}</strong></div><div className="topbar-actions"><span className="today-label">{new Intl.DateTimeFormat("en-BD", { dateStyle: "medium" }).format(new Date())}</span><button className="button button-quiet" onClick={exportReport}><ArrowDownToLine size={16} /> Export</button><button className="button button-primary button-compact" onClick={() => setSection("orders")}><Plus size={17} /> New order</button></div></header>
        <div className="page-content">
          <div className="page-intro"><div><p className="eyebrow">{section === "overview" ? "YOUR BUSINESS AT A GLANCE" : `MANAGE YOUR ${section.toUpperCase()}`}</p><h1>{section === "overview" ? `Good day, ${user.full_name.split(" ")[0]}.` : sectionTitle}</h1><p>{section === "overview" ? "Here’s where your business stands right now." : `Keep your ${section} organized and up to date.`}</p></div>{section === "overview" && <button className="date-filter" onClick={() => void refreshData()}><span className="online-dot" /> Live data <ChevronDown size={15} /></button>}</div>

          {error && <div className="alert alert-error" role="alert">{error}<button onClick={() => setError("")} aria-label="Dismiss error">×</button></div>}
          {notice && <div className="alert alert-success" role="status"><Check size={16} />{notice}<button onClick={() => setNotice("")} aria-label="Dismiss message">×</button></div>}

          {section === "overview" && <>
            <section className="metric-grid" aria-label="Business summary">{metrics.map(({ label, value, icon: Icon, color, caption }) => <article className="metric-card" key={label}><div className="metric-top"><span>{label}</span><span className={`metric-icon ${color}`}><Icon size={17} /></span></div><strong className="metric-value">৳{money(value)}</strong><small>{caption}</small></article>)}</section>
            <section className="overview-grid"><article className="panel trend-panel"><div className="panel-heading"><div><p className="eyebrow">ORDER ACTIVITY</p><h2>Recent orders</h2></div><button className="text-link" onClick={() => setSection("orders")}>All orders <ArrowRight size={15} /></button></div>{orders.length ? <div className="order-list">{orders.slice(0, 5).map((order) => <OrderRow key={order.id} order={order} customer={customers.find((item) => item.id === order.customer_id)?.name ?? "Customer"} />)}</div> : <EmptyState title="Your first order starts here" detail="Add a customer and product, then record the order to see your real numbers." action={<button className="button button-primary" onClick={() => setSection("orders")}><Plus size={16} /> Create an order</button>} />}</article>
              <article className="panel insight-panel"><div className="insight-illustration"><div className="sun-disc" /><div className="insight-bars"><i /><i /><i /><i /><i /><i /><i /></div><span className="insight-spark"><Sparkles size={16} /></span></div><p className="eyebrow">YOUR PROFIT PICTURE</p><h2>Know what you keep.</h2><p>Profit is calculated from your recorded sales, product costs, and operating expenses.</p><div className="profit-line"><span>Estimated net profit</span><strong>৳{money(summary?.estimated_profit_p ?? 0)}</strong></div><button className="button button-dark" onClick={exportReport}><ArrowDownToLine size={16} /> Download report</button></article></section>
            <section className="bottom-grid"><article className="panel compact-panel"><div className="panel-heading"><div><p className="eyebrow">INVENTORY WATCH</p><h2>Stock to watch</h2></div><button className="text-link" onClick={() => setSection("products")}>View products <ArrowRight size={15} /></button></div>{products.filter((product) => product.stock_qty <= product.low_stock_threshold).length ? products.filter((product) => product.stock_qty <= product.low_stock_threshold).slice(0, 4).map((product) => <div className="stock-row" key={product.id}><span className="stock-product-icon"><PackagePlus size={17} /></span><span className="stock-name"><strong>{product.name}</strong><small>{product.sku || "No SKU"}</small></span><span className="stock-level">{product.stock_qty} left</span></div>) : <p className="quiet-empty">No low-stock items. Add products to track your inventory.</p>}</article>
              <article className="quick-panel"><p className="eyebrow">SHORTCUTS</p><h2>Keep things moving.</h2><div className="shortcut-grid"><button onClick={() => setSection("orders")}><span className="shortcut-icon coral-icon"><ShoppingBag size={18} /></span><span><strong>Record an order</strong><small>Sale, payment, stock</small></span><ArrowRight size={15} /></button><button onClick={() => setSection("products")}><span className="shortcut-icon green-icon"><PackagePlus size={18} /></span><span><strong>Add a product</strong><small>Price and stock</small></span><ArrowRight size={15} /></button><button onClick={() => setSection("expenses")}><span className="shortcut-icon yellow-icon"><ReceiptText size={18} /></span><span><strong>Log an expense</strong><small>Keep profit honest</small></span><ArrowRight size={15} /></button></div></article></section>
          </>}

          {section === "orders" && <section className="workflow-grid"><article className="panel form-panel"><div className="panel-heading"><div><p className="eyebrow">SALES & PAYMENTS</p><h2>Record an order</h2></div><span className="step-mark">01</span></div>{(products.length === 0 || customers.length === 0) ? <EmptyState title="Set up your basics first" detail="An order needs at least one customer and one in-stock product."><div className="empty-actions"><button className="button button-secondary" onClick={() => setSection("products")}><Boxes size={16} /> Add product</button><button className="button button-secondary" onClick={() => setSection("customers")}><Users size={16} /> Add customer</button></div></EmptyState> : <OrderForm products={products} customers={customers} busy={busy} onSubmit={async (payload) => { setBusy(true); setError(""); setNotice(""); try { await request("/api/v1/orders", { method: "POST", body: JSON.stringify(payload) }); await refreshData(); setNotice("Order recorded. Stock and profit totals are updated."); } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not record order."); } finally { setBusy(false); } }} />}</article><article className="panel list-panel"><div className="panel-heading"><div><p className="eyebrow">ORDER HISTORY</p><h2>Latest orders <span className="count-pill">{orders.length}</span></h2></div><Search size={18} className="muted-icon" /></div>{orders.length ? <div className="order-list">{orders.map((order) => <OrderRow key={order.id} order={order} customer={customers.find((item) => item.id === order.customer_id)?.name ?? "Customer"} />)}</div> : <EmptyState title="No orders yet" detail="Orders you record will appear here." />}</article></section>}

          {section === "products" && <section className="workflow-grid"><ProductForm busy={busy} onSave={(event) => submitAction(event, "/api/v1/products", "Product saved. Your inventory is up to date.")} /><article className="panel list-panel"><div className="panel-heading"><div><p className="eyebrow">YOUR CATALOG</p><h2>Products <span className="count-pill">{products.length}</span></h2></div><Search size={18} className="muted-icon" /></div>{products.length ? <div className="table-wrap"><table><thead><tr><th>Product</th><th>Cost / price</th><th>In stock</th></tr></thead><tbody>{products.map((product) => <tr key={product.id}><td><strong>{product.name}</strong><small>{product.sku || product.category || "No category"}</small></td><td><strong>৳{money(product.unit_cost_p)} / ৳{money(product.selling_price_p)}</strong><small>Estimated margin ৳{money(product.selling_price_p - product.unit_cost_p)}</small></td><td><span className={`stock-pill ${product.stock_qty <= product.low_stock_threshold ? "low" : ""}`}>{product.stock_qty} units</span></td></tr>)}</tbody></table></div> : <EmptyState title="Your catalog is waiting" detail="Add products with their cost, price, and current stock." />}</article></section>}

          {section === "customers" && <section className="workflow-grid"><CustomerForm busy={busy} onSave={(event) => submitAction(event, "/api/v1/customers", "Customer added to your book.")} /><article className="panel list-panel"><div className="panel-heading"><div><p className="eyebrow">PEOPLE YOU SELL TO</p><h2>Customers <span className="count-pill">{customers.length}</span></h2></div><Search size={18} className="muted-icon" /></div>{customers.length ? <div className="customer-list">{customers.map((customer) => <div className="customer-row" key={customer.id}><span className="customer-avatar">{initials(customer.name)}</span><span className="customer-details"><strong>{customer.name}</strong><small>{customer.phone}{customer.address ? ` · ${customer.address}` : ""}</small></span><span className="customer-orders">{orders.filter((order) => order.customer_id === customer.id).length} orders</span></div>)}</div> : <EmptyState title="No customers added" detail="Save names and phone numbers so every order is easy to find." />}</article></section>}

          {section === "expenses" && <section className="workflow-grid"><ExpenseForm busy={busy} onSave={(event) => submitAction(event, "/api/v1/expenses", "Expense saved. Profit totals have been updated.")} /><article className="panel list-panel"><div className="panel-heading"><div><p className="eyebrow">MONEY OUT</p><h2>Recent expenses <span className="count-pill">{expenses.length}</span></h2></div><strong className="expense-total">৳{money(summary?.operating_expenses_p ?? 0)}</strong></div>{expenses.length ? <div className="expense-list">{expenses.map((expense) => <div className="expense-row" key={expense.id}><span className="expense-icon"><ReceiptText size={17} /></span><span className="expense-description"><strong>{expense.description}</strong><small>{expense.category} · {new Date(expense.expense_date).toLocaleDateString("en-BD", { dateStyle: "medium" })}</small></span><strong className="expense-amount">− ৳{money(expense.amount_p)}</strong></div>)}</div> : <EmptyState title="No expenses recorded" detail="Add delivery, packaging, or other operating costs to get a more honest profit picture." />}</article></section>}
          <footer className="app-footer"><span>MoneyTrack <span className="footer-dot">·</span> Keep the books simple.</span><span>BDT <span className="footer-dot">·</span> Business data is private</span></footer>
        </div>
      </section>
    </main>
  );
}

function OrderRow({ order, customer }: { order: Order; customer: string }) {
  return <div className="order-row"><span className="order-icon"><ShoppingBag size={17} /></span><span className="order-details"><strong>{order.order_number}</strong><small>{customer} · {order.items.map((item) => `${item.product_name_snapshot} ×${item.quantity}`).join(", ")}</small></span><span className="order-amount"><strong>৳{money(order.gross_total_p)}</strong><small className={order.outstanding_due_p ? "due-text" : "paid-text"}>{order.outstanding_due_p ? `৳${money(order.outstanding_due_p)} due` : "Paid in full"}</small></span></div>;
}

function OrderForm({ products, customers, busy, onSubmit }: { products: Product[]; customers: Customer[]; busy: boolean; onSubmit: (payload: Record<string, unknown>) => Promise<void> }) {
  const available = products.filter((product) => product.is_active && product.stock_qty > 0);
  const [customerId, setCustomerId] = useState(String(customers[0]?.id ?? ""));
  const [lines, setLines] = useState<OrderLine[]>([{ product_id: available[0]?.id ?? 0, quantity: 1 }]);
  const [discount, setDiscount] = useState("0");
  const [delivery, setDelivery] = useState("0");
  const [paid, setPaid] = useState("0");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const subtotal = lines.reduce((sum, line) => sum + (products.find((product) => product.id === line.product_id)?.selling_price_p ?? 0) * line.quantity, 0);
  const total = Math.max(subtotal + Number(delivery || 0) - Number(discount || 0), 0);
  return <form className="record-form" onSubmit={(event) => { event.preventDefault(); void onSubmit({ customer_id: Number(customerId), items: lines, discount_p: Number(discount), delivery_charge_p: Number(delivery), payment_amount_p: Number(paid), payment_method: paymentMethod }); }}>
    <Field label="Customer"><select value={customerId} onChange={(event) => setCustomerId(event.target.value)} required>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name} · {customer.phone}</option>)}</select></Field>
    <div className="line-heading"><span>Items</span><button type="button" className="text-link" onClick={() => setLines([...lines, { product_id: available[0]?.id ?? 0, quantity: 1 }])}><Plus size={15} /> Add line</button></div>
    {lines.map((line, index) => { const product = products.find((item) => item.id === line.product_id); return <div className="order-line" key={`${index}-${line.product_id}`}><select aria-label="Product" value={line.product_id} onChange={(event) => setLines(lines.map((entry, lineIndex) => lineIndex === index ? { ...entry, product_id: Number(event.target.value) } : entry))}>{available.map((item) => <option key={item.id} value={item.id}>{item.name} · ৳{money(item.selling_price_p)} · {item.stock_qty} left</option>)}</select><input aria-label="Quantity" type="number" min="1" max={product?.stock_qty ?? 1} value={line.quantity} onChange={(event) => setLines(lines.map((entry, lineIndex) => lineIndex === index ? { ...entry, quantity: Math.max(1, Number(event.target.value)) } : entry))} /><button type="button" className="remove-line" aria-label="Remove item" disabled={lines.length === 1} onClick={() => setLines(lines.filter((_, lineIndex) => lineIndex !== index))}>×</button></div>; })}
    <div className="form-two"><Field label="Discount (৳)"><input type="number" min="0" value={discount} onChange={(event) => setDiscount(event.target.value)} /></Field><Field label="Delivery (৳)"><input type="number" min="0" value={delivery} onChange={(event) => setDelivery(event.target.value)} /></Field></div>
    <div className="form-two"><Field label="Paid now (৳)"><input type="number" min="0" max={total} value={paid} onChange={(event) => setPaid(event.target.value)} /></Field><Field label="Payment method"><select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}><option value="cash">Cash</option><option value="mobile_banking">Mobile banking</option><option value="bank">Bank transfer</option></select></Field></div>
    <div className="order-total"><span>Order total</span><strong>৳{money(total)}</strong></div>
    <button className="button button-primary form-submit" disabled={busy || available.length === 0}>{busy ? "Saving order..." : "Save order"}<ArrowRight size={16} /></button>
  </form>;
}

function ProductForm({ busy, onSave }: { busy: boolean; onSave: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  return <article className="panel form-panel"><div className="panel-heading"><div><p className="eyebrow">INVENTORY</p><h2>Add a product</h2></div><span className="step-mark"><PackagePlus size={17} /></span></div><form className="record-form" onSubmit={(event) => { void onSave(event); }}><Field label="Product name"><input name="name" required placeholder="e.g. Cotton kurti" /></Field><div className="form-two"><Field label="SKU (Stock Keeping Unit)"><input name="sku" placeholder="Optional inventory code" /></Field><Field label="Category"><input name="category" placeholder="e.g. Clothing" /></Field></div><div className="form-two"><Field label="Unit cost (৳)"><input name="unit_cost_p" type="number" min="0" required defaultValue="0" /></Field><Field label="Selling price (৳)"><input name="selling_price_p" type="number" min="0" required defaultValue="0" /></Field></div><div className="form-two"><Field label="Opening stock"><input name="stock_qty" type="number" min="0" required defaultValue="0" /></Field><Field label="Low stock alert at"><input name="low_stock_threshold" type="number" min="0" defaultValue="5" /></Field></div><input type="hidden" name="is_active" value="true" /><button className="button button-primary form-submit" disabled={busy}>{busy ? "Saving..." : "Save product"}<ArrowRight size={16} /></button></form></article>;
}

function CustomerForm({ busy, onSave }: { busy: boolean; onSave: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  return <article className="panel form-panel"><div className="panel-heading"><div><p className="eyebrow">YOUR PEOPLE</p><h2>Add a customer</h2></div><span className="step-mark"><Users size={17} /></span></div><form className="record-form" onSubmit={(event) => { void onSave(event); }}><Field label="Full name"><input name="name" required placeholder="e.g. Nusrat Jahan" /></Field><Field label="Phone number"><input name="phone" type="tel" required placeholder="01XXXXXXXXX" /></Field><Field label="Delivery address"><textarea name="address" rows={3} placeholder="Optional address" /></Field><Field label="Notes"><textarea name="notes" rows={3} placeholder="Preferences or order notes" /></Field><button className="button button-primary form-submit" disabled={busy}>{busy ? "Saving..." : "Save customer"}<ArrowRight size={16} /></button></form></article>;
}

function ExpenseForm({ busy, onSave }: { busy: boolean; onSave: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  return <article className="panel form-panel"><div className="panel-heading"><div><p className="eyebrow">MONEY OUT</p><h2>Log an expense</h2></div><span className="step-mark"><ReceiptText size={17} /></span></div><form className="record-form" onSubmit={(event) => { void onSave(event); }}><Field label="What was it for?"><input name="description" required placeholder="e.g. Packaging supplies" /></Field><Field label="Category"><select name="category"><option value="delivery">Delivery</option><option value="packaging">Packaging</option><option value="supplies">Supplies</option><option value="marketing">Marketing</option><option value="other">Other</option></select></Field><Field label="Amount (৳)"><input name="amount_p" type="number" min="1" required placeholder="0" /></Field><Field label="Paid with"><select name="payment_method"><option value="cash">Cash</option><option value="mobile_banking">Mobile banking</option><option value="bank">Bank transfer</option></select></Field><button className="button button-primary form-submit" disabled={busy}>{busy ? "Saving..." : "Save expense"}<ArrowRight size={16} /></button></form></article>;
}
