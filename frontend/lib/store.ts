"use client";

import type { RecommendationResponse, StudentProfile } from "./types";

const PROFILE_KEY = "compass.profile.v1";
const RESULT_KEY = "compass.lastResult.v1";

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
