"use client";

import Link from "next/link";
import { CompassMark } from "./CompassMark";
import type { StudentProfile } from "@/lib/types";

export function ChatSidebar({
  profile,
  onNewChat,
  onLogout,
}: {
  profile: StudentProfile | null;
  onNewChat: () => void;
  onLogout: () => void;
}) {
  return (
    <aside
      className="hidden w-64 shrink-0 flex-col border-r border-hairline lg:flex"
      style={{ background: "var(--parchment-raised)" }}
    >
      <div className="flex items-center gap-2 px-4 py-4">
        <span
          className="flex h-8 w-8 items-center justify-center rounded-xl text-white shadow-sm"
          style={{ background: "linear-gradient(135deg, var(--brass), var(--deep-teal))" }}
        >
          <CompassMark size={17} />
        </span>
        <span className="font-display text-base">Capstone Compass</span>
      </div>

      <div className="px-3">
        <button
          type="button"
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-xl border border-hairline px-3 py-2 text-sm transition-colors hover:border-brass hover:text-brass"
        >
          <span aria-hidden className="text-base leading-none">＋</span> New chat
        </button>
      </div>

      {profile && (
        <div className="mx-3 mt-4 overflow-hidden rounded-xl border border-hairline">
          <div className="h-1" style={{ background: "linear-gradient(90deg, var(--brass), var(--deep-teal))" }} />
          <div className="p-3">
            <p className="readout-label">Signed in as</p>
            <p className="mt-0.5 truncate font-medium">{profile.name}</p>
            <p className="data-token mt-1 text-xs text-charcoal-text/55">
              comfort: {profile.tech_comfort}
            </p>
            {(profile.skills.length > 0 || profile.interests.length > 0) && (
              <div className="mt-2 flex flex-wrap gap-1">
                {[...profile.skills, ...profile.interests].slice(0, 8).map((t) => (
                  <span key={t} className="pill">
                    {t}
                  </span>
                ))}
              </div>
            )}
            <Link href="/login" className="link-teal mt-2 inline-block text-xs">
              Edit profile
            </Link>
          </div>
        </div>
      )}

      <div className="flex-1" />

      <div className="border-t border-hairline p-3">
        <button
          type="button"
          onClick={onLogout}
          className="w-full rounded-lg px-2 py-1.5 text-left text-sm text-charcoal-text/70 hover:bg-parchment hover:text-charcoal-text"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
