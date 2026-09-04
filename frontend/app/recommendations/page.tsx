"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * The two-pane workspace was replaced by the /chat conversational UI.
 * This route stays as a redirect so old links / bookmarks don't 404.
 */
export default function RecommendationsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/chat");
  }, [router]);
  return null;
}
