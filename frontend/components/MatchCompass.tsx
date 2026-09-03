"use client";

import { useEffect, useRef, useState } from "react";
import { fmt } from "@/lib/format";

const SWEEP = 240; // degrees, -120 .. +120

/**
 * A minimal radial dial - a needle finding a bearing - not a progress bar.
 * The needle position is the real cosine similarity on a fixed 0..scaleMax scale,
 * so it can never read "full / perfect". On first paint the needle does the one
 * deliberate "settling" motion, then holds.
 */
export function MatchCompass({
  similarity,
  band,
  scaleMax = 0.5,
  size = 116,
  settle = true,
}: {
  similarity: number;
  band: "strong" | "moderate" | "weak";
  scaleMax?: number;
  size?: number;
  settle?: boolean;
}) {
  const frac = Math.max(0, Math.min(1, similarity / scaleMax));
  const target = -SWEEP / 2 + frac * SWEEP;
  const [angle, setAngle] = useState(settle ? -SWEEP / 2 : target);
  const needleRef = useRef<SVGGElement>(null);

  useEffect(() => {
    if (!settle) {
      setAngle(target);
      return;
    }
    const el = needleRef.current;
    if (!el) return;
    el.style.setProperty("--needle-to", `${target}deg`);
    el.classList.remove("needle-settling");
    // force reflow so the animation restarts on new results
    void el.getBoundingClientRect();
    el.classList.add("needle-settling");
    const done = () => setAngle(target);
    el.addEventListener("animationend", done, { once: true });
    // fallback if reduced-motion cancels the animation event
    const t = setTimeout(done, 1400);
    return () => {
      el.removeEventListener("animationend", done);
      clearTimeout(t);
    };
  }, [target, settle]);

  const r = 50;
  const cx = 60;
  const cy = 60;
  const arc = (deg: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [cx + Math.cos(rad) * r, cy + Math.sin(rad) * r];
  };
  const [x0, y0] = arc(-SWEEP / 2);
  const [x1, y1] = arc(SWEEP / 2);
  const [xv, yv] = arc(target);

  const bandColor =
    band === "strong" ? "var(--deep-teal)" : band === "moderate" ? "var(--brass)" : "var(--charcoal-muted)";

  return (
    <div className="flex flex-col items-center gap-1" style={{ width: size }}>
      <svg width={size} height={size * 0.86} viewBox="0 0 120 104" aria-hidden="true">
        {/* track */}
        <path
          d={`M ${x0} ${y0} A ${r} ${r} 0 1 1 ${x1} ${y1}`}
          fill="none"
          stroke="var(--hairline)"
          strokeWidth={6}
          strokeLinecap="round"
        />
        {/* filled portion to the reading (large-arc only past 3/4 of the 240deg sweep) */}
        <path
          d={`M ${x0} ${y0} A ${r} ${r} 0 ${frac > 0.75 ? 1 : 0} 1 ${xv} ${yv}`}
          fill="none"
          stroke={bandColor}
          strokeWidth={6}
          strokeLinecap="round"
        />
        {/* cardinal ticks */}
        {[-120, -60, 0, 60, 120].map((d) => {
          const [ix, iy] = arc(d);
          const rad = ((d - 90) * Math.PI) / 180;
          const [ox, oy] = [cx + Math.cos(rad) * (r + 7), cy + Math.sin(rad) * (r + 7)];
          return (
            <line
              key={d}
              x1={ix}
              y1={iy}
              x2={ox}
              y2={oy}
              stroke="var(--charcoal-muted)"
              strokeWidth={1}
              opacity={0.5}
            />
          );
        })}
        {/* needle */}
        <g ref={needleRef} style={{ transform: `rotate(${angle}deg)`, transformOrigin: "60px 60px" }}>
          <path d={`M 60 18 L 63 60 L 57 60 Z`} fill="var(--charcoal-text)" />
          <circle cx="60" cy="60" r="4.5" fill="var(--charcoal-text)" />
          <circle cx="60" cy="60" r="2" fill="var(--parchment-raised)" />
        </g>
        <text
          x="60"
          y="94"
          textAnchor="middle"
          className="data-token"
          fontSize="15"
          fill="var(--charcoal-text)"
        >
          {fmt(similarity)}
        </text>
      </svg>
      <span className="readout-label -mt-1">cosine similarity</span>
      <span className="text-xs font-medium" style={{ color: bandColor }}>
        {band} signal
      </span>
    </div>
  );
}
