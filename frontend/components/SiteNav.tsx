"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CompassMark } from "./CompassMark";
import { sessionStore } from "@/lib/store";
import type { Session } from "@/lib/types";

// Admin + About stay reachable by direct URL (and a small link in the footer)
// but are deliberately not surfaced in the student-facing nav.
// the chat + login screens own their full-height layout and header
const HIDDEN_ON = ["/chat", "/login"];

export function SiteNav() {
  const path = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    setSession(sessionStore.get());
  }, [path]);

  if (HIDDEN_ON.some((p) => path.startsWith(p))) return null;

  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-parchment-raised">
      <nav className="mx-auto flex max-w-chart flex-col gap-1 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6 sm:py-3">
        <Link href="/" className="flex items-center gap-2.5 text-charcoal-text">
          <span className="text-brass">
            <CompassMark size={24} />
          </span>
          <span className="font-display text-base leading-none sm:text-lg">
            Capstone&nbsp;Compass
          </span>
        </Link>
        <div className="flex items-center justify-between gap-2 sm:gap-4">
          {session && (
            <Link
              href="/chat"
              aria-current={path.startsWith("/chat") ? "page" : undefined}
              className={`block whitespace-nowrap rounded-sm px-2 py-1.5 text-sm underline-offset-[6px] transition-colors hover:text-brass sm:px-2.5 ${
                path.startsWith("/chat") ? "text-brass underline decoration-2" : "text-charcoal-text/65"
              }`}
            >
              Chat
            </Link>
          )}
          {session ? (
            <button
              type="button"
              onClick={() => {
                sessionStore.clear();
                setSession(null);
                router.push("/login");
              }}
              className="pill shrink-0 hover:border-brass hover:text-brass"
            >
              {session.name.split(" ")[0]} · Log out
            </button>
          ) : (
            <Link href="/login" className="btn btn-primary !py-1.5 shrink-0 text-xs">
              Log in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
