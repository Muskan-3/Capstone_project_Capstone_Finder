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

/**
 * Turn the backend's precise-but-technical `message`/`refinement` payload
 * into one natural sentence for the chat bubble. The full technical message
 * is never discarded - it's kept as `detail` and shown behind a toggle -
 * this is purely a friendlier headline, not a different claim.
 */
export function friendlyLead(res: {
  mode: string;
  cluster_confidence: number;
  cluster_distribution: { label: string }[];
  refinement?: { negative: string[]; positive: string[] } | null;
}): string {
  if (res.mode === "no_signal") {
    return "I couldn't match any of that to the catalogue's vocabulary - try naming a specific tool, technique, or problem domain.";
  }
  if (res.mode === "low_confidence") {
    return (
      `I don't have a strong match for that yet (closest domain fit: ${fmt(res.cluster_confidence)}). ` +
      "Here are the nearest statements, shown with their real scores - treat them as weak leads, not recommendations."
    );
  }
  const domain = res.cluster_distribution[0]?.label;
  let lead = domain ? `Closest domain: “${domain}”.` : "Here's what I found.";
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
