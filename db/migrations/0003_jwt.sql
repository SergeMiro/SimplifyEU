-- Phase 4b (web): Better Auth `jwt` plugin table for SimplifyEU.
-- Backs /api/auth/token (mint JWT) and /api/auth/jwks (public keys).
-- id is UUID to match generateId: "uuid". Mirrors apps/web/src/db/auth-schema.ts.

BEGIN;

-- jwks ------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jwks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  public_key  TEXT NOT NULL,
  private_key TEXT NOT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT now(),
  expires_at  TIMESTAMP
);

COMMIT;
