/**
 * Drizzle database client for the SimplifyEU web app.
 *
 * Uses a node-postgres Pool against DATABASE_URL. This replaces the Supabase
 * client for direct DB access (Phase 3 migration off Supabase). Better Auth
 * talks to this `db` via the drizzle adapter (see src/lib/auth.ts).
 */

import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";

import * as schema from "./schema";

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  throw new Error("DATABASE_URL is not set");
}

export const pool = new Pool({ connectionString });

export const db = drizzle(pool, { schema });
