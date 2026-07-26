export function Card({ title, action, className = "", children }) {
  return (
    <section className={`bg-white rounded-xl2 shadow-card border border-ink-100 p-5 ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between mb-4">
          {title && <h2 className="font-semibold text-ink-900">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatCard({ label, value, delta, deltaLabel = "vs last month", tone = "up" }) {
  return (
    <Card className="!p-4">
      <p className="text-xs text-ink-500">{label}</p>
      <p className="text-2xl font-bold text-ink-900 mt-1">{value ?? "—"}</p>
      {delta != null && (
        <p className={`text-xs mt-1 font-medium ${tone === "up" ? "text-brand-600" : "text-risk-veryhigh"}`}>
          {tone === "up" ? "↑" : "↓"} {delta} {deltaLabel}
        </p>
      )}
    </Card>
  );
}
