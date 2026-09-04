"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Not wired up yet. The login/chat flow currently runs on a local-only
 * session (see lib/store.ts) plus the FastAPI backend's own `students`
 * table - there is no live Supabase project behind this client.
 *
 * To switch the student database over to Supabase:
 *   1. Create a project at supabase.com, then set in frontend/.env.local:
 *        NEXT_PUBLIC_SUPABASE_URL=...
 *        NEXT_PUBLIC_SUPABASE_ANON_KEY=...
 *   2. Add a `students` table (or reuse the shape in lib/types.ts) and, if
 *      you want real accounts, turn on Supabase Auth (email/password or
 *      magic link) and swap sessionStore in lib/store.ts for
 *      supabase.auth.getSession() / onAuthStateChange().
 *   3. Point app/login/page.tsx's submit handler at supabase.auth.signUp /
 *      signInWithPassword instead of - or in addition to - api.saveStudent().
 *
 * `getSupabase()` returns null until both env vars are set, so nothing here
 * throws or silently no-ops against a placeholder project.
 */
let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  if (!client) client = createClient(url, key);
  return client;
}

export const supabaseConfigured = () => Boolean(getSupabase());
