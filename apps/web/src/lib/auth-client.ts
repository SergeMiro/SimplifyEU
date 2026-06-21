/**
 * Better Auth browser client. Used by the register / login pages
 * (signUp.email, signIn.email) and any other client-side auth calls.
 */

import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL,
});

export const { signIn, signUp, signOut, useSession } = authClient;
