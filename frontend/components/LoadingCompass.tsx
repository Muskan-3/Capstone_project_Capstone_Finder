import { CompassMark } from "./CompassMark";

export function LoadingCompass({ label = "Taking a bearing…" }: { label?: string }) {
  return (
    <div className="relative overflow-hidden rounded-card border border-hairline bg-parchment-raised py-20">
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <span className="compass-rose-watermark">
          <CompassMark size={360} watermark />
        </span>
      </div>
      <div className="relative flex flex-col items-center gap-3">
        <span className="needle-settling text-brass" style={{ ["--needle-to" as string]: "0deg" }}>
          <CompassMark size={40} />
        </span>
        <p className="data-token text-sm text-charcoal-text/70">{label}</p>
      </div>
    </div>
  );
}
