/**
 * The compass-rose motif. Small = wordmark glyph in the nav. Large + `watermark`
 * = the single faint background moment behind the loading state (Section 10).
 */
export function CompassMark({
  size = 24,
  watermark = false,
  className = "",
}: {
  size?: number;
  watermark?: boolean;
  className?: string;
}) {
  const stroke = watermark ? 1.1 : 1.4;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role="img"
      aria-label="Capstone Compass"
      className={className}
      fill="none"
    >
      <circle cx="24" cy="24" r="21" stroke="currentColor" strokeWidth={stroke} opacity={0.5} />
      <circle cx="24" cy="24" r="15" stroke="currentColor" strokeWidth={stroke} opacity={0.28} />
      {/* eight-point rose */}
      {Array.from({ length: 8 }).map((_, i) => {
        const a = (i * Math.PI) / 4;
        const long = i % 2 === 0;
        const r = long ? 20 : 11;
        const x = 24 + Math.sin(a) * r;
        const y = 24 - Math.cos(a) * r;
        return (
          <line
            key={i}
            x1="24"
            y1="24"
            x2={x}
            y2={y}
            stroke="currentColor"
            strokeWidth={long ? stroke : stroke * 0.7}
            opacity={long ? 0.7 : 0.35}
          />
        );
      })}
      {/* the needle: north half filled */}
      <path d="M24 6 L27.4 24 L24 24 Z" fill="currentColor" opacity={0.92} />
      <path d="M24 42 L20.6 24 L24 24 Z" fill="currentColor" opacity={0.4} />
      <circle cx="24" cy="24" r="2.4" fill="currentColor" />
    </svg>
  );
}
