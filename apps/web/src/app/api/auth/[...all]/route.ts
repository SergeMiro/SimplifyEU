/**
 * Better Auth catch-all route handler.
 * Mounts the Better Auth server at /api/auth/* (sign-up, sign-in, session, etc.).
 */

import { toNextJsHandler } from "better-auth/next-js";

import { auth } from "@/lib/auth";

export const { GET, POST } = toNextJsHandler(auth);
