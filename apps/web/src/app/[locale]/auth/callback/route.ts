import { NextResponse } from "next/server";

/**
 * OAuth callback route.
 *
 * Email + password auth (Phase 3 part 1) does not use this callback — Better
 * Auth handles the whole email/password flow under /api/auth/*. This is kept as
 * a clean no-op redirect so any stale links don't 404.
 *
 * TODO (part 2): when Google / Apple OAuth is added, Better Auth's social flow
 * uses its own callback at /api/auth/callback/<provider>, so this route can
 * either be removed or repurposed for a post-login landing redirect.
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const next = searchParams.get("next") ?? "/dashboard";

  // Validate redirect path to prevent open redirect attacks.
  const safePath =
    next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";

  return NextResponse.redirect(`${origin}${safePath}`);
}
