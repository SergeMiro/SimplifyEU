/**
 * Better Auth browser client. Used by the register / login pages
 * (signUp.email, signIn.email) and any other client-side auth calls.
 */

import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL,
});

export const { signIn, signUp, signOut, useSession } = authClient;

/**
 * Mint a Better Auth JWT for the current session via the `jwt` plugin's
 * /api/auth/token endpoint. Sent as `Authorization: Bearer <jwt>` to the
 * Python services. Returns null when there is no active session.
 */
export async function getAuthToken(): Promise<string | null> {
  const baseURL = process.env.NEXT_PUBLIC_BETTER_AUTH_URL ?? "";
  const res = await fetch(`${baseURL}/api/auth/token`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { token?: string };
  return data.token ?? null;
}
