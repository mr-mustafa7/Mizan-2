interface StatCardProps {
  label: string;
  value: number | string;
  hint?: string;
  accent?: "teal" | "amber" | "rose" | "slate";
}

const accentStyles = {
  teal: "border-teal-200 bg-teal-50 text-teal-700",
  amber: "border-amber-200 bg-amber-50 text-amber-700",
  rose: "border-rose-200 bg-rose-50 text-rose-700",
  slate: "border-slate-200 bg-white text-slate-700",
};

export function StatCard({ label, value, hint, accent = "slate" }: StatCardProps) {
  return (
    <div className={`rounded-xl border p-5 shadow-sm ${accentStyles[accent]}`}>
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
        {value}
      </p>
      {hint && <p className="mt-1 text-xs opacity-70">{hint}</p>}
    </div>
  );
}
