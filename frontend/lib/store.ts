"use client";

import type { ChatMessage, RecommendationResponse, Session, StudentProfile } from "./types";

const PROFILE_KEY = "compass.profile.v1";
const RESULT_KEY = "compass.lastResult.v1";
const SESSION_KEY = "compass.session.v1";
const CHAT_KEY = "compass.chat.v1";

function read<T>(key: string): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode / disabled storage - the app still works, just doesn't remember */
  }
}

export const profileStore = {
  get: () => read<StudentProfile>(PROFILE_KEY),
  set: (p: StudentProfile) => write(PROFILE_KEY, p),
  clear: () => {
    try {
      window.localStorage.removeItem(PROFILE_KEY);
      window.localStorage.removeItem(RESULT_KEY);
    } catch {
      /* noop */
    }
  },
};

export const resultStore = {
  get: () => read<RecommendationResponse>(RESULT_KEY),
  set: (r: RecommendationResponse) => write(RESULT_KEY, r),
};

/**
 * A lightweight, local-only "session". There is no password/account backend
 * (Section 8's schema has no users table) - the login page still collects a
 * name + email + password, but only the name/email are ever sent to the API
 * (as the student profile). The password just gates entry to this browser's
 * session; it is never transmitted or verified server-side. That's an
 * intentional MVP shortcut, not an oversight - flagged in the login page copy.
 */
export const sessionStore = {
  get: () => read<Session>(SESSION_KEY),
  set: (s: Session) => write(SESSION_KEY, s),
  clear: () => {
    try {
      window.localStorage.removeItem(SESSION_KEY);
      window.localStorage.removeItem(CHAT_KEY);
    } catch {
      /* noop */
    }
  },
};

export const chatStore = {
  get: (studentId: number) => read<ChatMessage[]>(`${CHAT_KEY}.${studentId}`) ?? [],
  set: (studentId: number, messages: ChatMessage[]) => write(`${CHAT_KEY}.${studentId}`, messages),
  clear: (studentId: number) => {
    try {
      window.localStorage.removeItem(`${CHAT_KEY}.${studentId}`);
    } catch {
      /* noop */
    }
  },
};
