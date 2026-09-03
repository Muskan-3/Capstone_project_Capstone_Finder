export const fmt = (n: number, digits = 3) =>
  Number.isFinite(n) ? n.toFixed(digits) : "-";

export const pct = (n: number, digits = 0) =>
  Number.isFinite(n) ? `${(n * 100).toFixed(digits)}%` : "-";

export const shortDate = (iso: string | null) => {
  if (!iso) return "-";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "-"
    : d.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
};

export const bandLabel: Record<string, string> = {
  strong: "strong signal",
  moderate: "moderate signal",
  weak: "weak signal",
};
