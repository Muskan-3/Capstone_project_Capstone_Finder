"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Onboarding was folded into /login (step 2 of that form collects the same
 * profile). This route stays as a redirect so old links / bookmarks don't 404.
 */
export default function OnboardingRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/login");
  }, [router]);
  return null;
}
