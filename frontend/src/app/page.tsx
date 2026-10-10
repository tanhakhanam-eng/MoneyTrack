const metrics = [
  { label: "Today sales", value: "৳8,500", tone: "emerald" },
  { label: "Collected", value: "৳6,300", tone: "green" },
  { label: "Expenses", value: "৳2,000", tone: "amber" },
  { label: "Due", value: "৳1,500", tone: "rose" },
];

const activities = [
  { name: "Order #HF-1024", detail: "Shirt set · paid 40%", status: "Confirmed" },
  { name: "Low stock", detail: "Face serum 12 units left", status: "Review" },
  { name: "Courier fee", detail: "৳120 for delivery", status: "Expense" },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f4f8f4] text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-10 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">
              HisabFlow
            </p>
            <h1 className="mt-2 text-3xl font-bold text-slate-900">
              Know your numbers. Grow your business.
            </h1>
          </div>
          <div className="flex gap-3">
            <button className="rounded-full border border-emerald-700 px-4 py-2 text-sm font-medium text-emerald-700">
              Login
            </button>
            <button className="rounded-full bg-emerald-700 px-4 py-2 text-sm font-medium text-white shadow-sm">
              Start free
            </button>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-4">
          {metrics.map((metric) => (
            <article
              key={metric.label}
              className="rounded-2xl border border-emerald-100 bg-white p-5 shadow-sm"
            >
              <p className="text-sm text-slate-500">{metric.label}</p>
              <p className="mt-3 text-2xl font-bold text-slate-900">{metric.value}</p>
              <span className="mt-3 inline-flex rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">
                Live
              </span>
            </article>
          ))}
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-emerald-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Today</p>
                <h2 className="mt-2 text-4xl font-bold">৳2,100</h2>
              </div>
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
                Estimated profit
              </span>
            </div>

            <div className="mt-6 h-44 rounded-2xl bg-gradient-to-br from-emerald-50 via-white to-amber-50 p-4">
              <div className="flex h-full items-end gap-3">
                {[32, 52, 40, 68, 58, 85, 76].map((bar, index) => (
                  <div
                    key={index}
                    className="flex-1 rounded-t-xl bg-emerald-500/80"
                    style={{ height: `${bar}%` }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
            <p className="text-sm uppercase tracking-[0.2em] text-emerald-300">Quick actions</p>
            <div className="mt-5 space-y-3">
              <button className="w-full rounded-2xl bg-emerald-600 px-4 py-3 text-left text-sm font-medium text-white">
                + New Order
              </button>
              <button className="w-full rounded-2xl border border-slate-700 px-4 py-3 text-left text-sm font-medium text-slate-100">
                Add Expense
              </button>
              <button className="w-full rounded-2xl border border-slate-700 px-4 py-3 text-left text-sm font-medium text-slate-100">
                Export Report
              </button>
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.25fr_1fr]">
          <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
            <h3 className="text-xl font-semibold">Recent activity</h3>
            <div className="mt-4 space-y-4">
              {activities.map((activity) => (
                <div key={activity.name} className="flex items-center justify-between rounded-2xl bg-slate-50 p-3">
                  <div>
                    <p className="font-medium text-slate-800">{activity.name}</p>
                    <p className="text-sm text-slate-500">{activity.detail}</p>
                  </div>
                  <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-700">
                    {activity.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl bg-gradient-to-br from-emerald-700 to-emerald-900 p-6 text-white shadow-sm">
            <p className="text-sm uppercase tracking-[0.2em] text-emerald-200">Focus</p>
            <h3 className="mt-3 text-2xl font-bold">Order to profit flow</h3>
            <p className="mt-3 text-sm leading-6 text-emerald-100">
              Create products, record deliveries, collect payments, and track contribution profit without guesswork.
            </p>
            <div className="mt-5 rounded-2xl bg-white/10 p-4 text-sm text-emerald-50">
              Built for homemade sellers, boutique shops, and daily order-based businesses in Bangladesh.
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
