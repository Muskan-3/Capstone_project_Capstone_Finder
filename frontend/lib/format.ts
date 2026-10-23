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

/**
 * Turn the backend's precise-but-technical `message`/`refinement` payload
 * into one natural sentence for the chat bubble. The full technical message
 * is never discarded - it's kept as `detail` and shown behind a toggle -
 * this is purely a friendlier headline, not a different claim. No scores:
 * those stay internal.
 */
export function friendlyLead(res: {
  mode: string;
  routed_domains: string[];
  suggested_domains: string[];
  refinement?: { negative: string[]; positive: string[] } | null;
  recommendations?: unknown[];
}): string {
  const shown = res.recommendations?.length ?? 0;
  if (res.mode === "off_topic" || res.mode === "no_signal") {
    const domains = res.suggested_domains.length ? ` Try one of these domains: ${res.suggested_domains.join(", ")}.` : "";
    return `I couldn't find projects that match that.${domains}`;
  }
  if (shown === 0) {
    return "Everything that matched was filtered out by your constraints - try loosening one.";
  }
  const domain = res.routed_domains.join(" + ");
  let lead = domain ? `From ${domain}:` : "Here's what I found.";
  if (res.refinement) {
    const bits: string[] = [];
    if (res.refinement.positive.length) {
      bits.push(`leaning into ${res.refinement.positive.slice(0, 3).join(", ")}`);
    }
    if (res.refinement.negative.length) {
      bits.push(`steering away from ${res.refinement.negative.slice(0, 3).join(", ")}`);
    }
    if (bits.length) lead += ` Adjusted, ${bits.join(" and ")}.`;
  }
  return lead;
}
