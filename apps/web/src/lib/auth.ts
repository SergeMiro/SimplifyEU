/**
 * Better Auth server configuration (Phase 3 — email/password auth).
 *
 * Email + password only for now. Google OAuth is intentionally deferred to
 * part 2 when provider keys arrive — see the `socialProviders` TODO below.
 *
 * IDs: user.id (and session/account/verification ids) are UUIDs so they match
 * the existing `uuid` foreign keys across the app schema. This is configured via
 * `advanced.database.generateId: "uuid"`, which makes Better Auth generate
 * UUIDs and the generated auth tables use `uuid` id columns.
 *
 * Profile link: when a Better Auth user is created we insert a matching row into
 * the app `users` profile table with the SAME id, so app FKs that reference
 * `users(id)` resolve. The `users(id)` -> `"user"(id)` FK is added in the
 * applied auth-tables migration.
 */

import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { jwt } from "better-auth/plugins";

import { db } from "@/db/client";
import { users } from "@/db/schema";

export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: "pg",
  }),
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BETTER_AUTH_URL,
  emailAndPassword: {
    enabled: true,
  },
  advanced: {
    database: {
      // Generate UUID ids to match the existing uuid FKs in the app schema.
      generateId: "uuid",
    },
  },
  // JWT plugin: exposes /api/auth/token (mint a JWT for the current session) and
  // /api/auth/jwks (public keys for verification). The web app sends this JWT as
  // `Authorization: Bearer <jwt>` to the Python services. Needs a `jwks` table
  // (see src/db/auth-schema.ts / db/migrations/0003_jwt.sql).
  plugins: [jwt()],
  databaseHooks: {
    user: {
      create: {
        // After Better Auth inserts the auth `user` row, mirror it into the app
        // `users` profile table with the SAME id so app FKs to users(id) resolve.
        after: async (user) => {
          await db
            .insert(users)
            .values({
              id: user.id,
              fullName: user.name ?? null,
              avatarUrl: user.image ?? null,
            })
            .onConflictDoNothing();
        },
      },
    },
  },
  // TODO (part 2): add the Google social provider once OAuth keys arrive, e.g.
  //   socialProviders: {
  //     google: { clientId: ..., clientSecret: ... },
  //   }
});
