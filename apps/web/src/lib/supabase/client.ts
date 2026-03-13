import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    if (typeof window !== "undefined") {
      console.warn("Supabase credentials are missing. Auth features will not work.");
    }
    // Return a dummy client or handle it gracefully
    // We'll return the client anyway, it will just fail on actual calls
    return createBrowserClient(
      url || "https://placeholder.supabase.co",
      key || "placeholder-key"
    );
  }

  return createBrowserClient(url, key);
}