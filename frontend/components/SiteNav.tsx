"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CompassMark } from "./CompassMark";

const LINKS = [
  { href: "/onboarding", label: "Start" },
  { href: "/recommendations", label: "Workspace" },
  { href: "/admin", label: "Admin" },
  { href: "/about", label: "How it works" },
];

export function SiteNav() {
  const path = usePathname();
  return (
    <header
      className="sticky top-0 z-40 bg-ink"
      style={{ color: "var(--on-ink)" }}
    >
      <nav className="mx-auto flex max-w-chart flex-col gap-1 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6 sm:py-3">
        <Link href="/" className="flex items-center gap-2.5" style={{ color: "var(--on-ink)" }}>
          <span style={{ color: "var(--on-ink-accent)" }}>
            <CompassMark size={24} />
          </span>
          <span className="font-display text-base leading-none sm:text-lg">
            Capstone&nbsp;Compass
          </span>
        </Link>
        <ul className="-mx-1 flex items-center gap-0.5 overflow-x-auto text-[13px] sm:mx-0 sm:gap-1 sm:text-sm">
          {LINKS.map((l) => {
            const active = path === l.href || (l.href !== "/" && path.startsWith(l.href));
            return (
              <li key={l.href} className="shrink-0">
                <Link
                  href={l.href}
                  aria-current={active ? "page" : undefined}
                  className="block whitespace-nowrap rounded-sm px-2 py-1.5 underline-offset-[6px] transition-colors hover:underline sm:px-2.5"
                  style={{
                    color: active ? "var(--on-ink)" : "var(--on-ink-dim)",
                    textDecorationLine: active ? "underline" : undefined,
                    textDecorationColor: "var(--brass)",
                    textDecorationThickness: active ? "2px" : undefined,
                  }}
                >
                  {l.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
