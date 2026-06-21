# SimplifyEU — Phase 6 parity verification + Phase 7 cutover notes

Date: 2026-06-21
Branch: `migrate/postgres`
Repo: `/srv/sergiy_prod/SimplifyEU`
Verified by: end-to-end harness (throwaway scripts/venv, no source changes, no commit).

---

## TL;DR

| Check | Result |
|-------|--------|
| Real Better Auth JWT minted same-process (EdDSA) | YES |
| JWKS exported (1 key, EdDSA / OKP / Ed25519) | YES |
| BA writes persist to live `simplifyeu_db` (`user` + `users` mirror + `jwks`) | YES |
| EdDSA signature validates in Python via PyJWKClient, `sub` == user uuid | YES |
| **Service `verify_jwt` accepts the real BA token (UNMODIFIED code)** | **NO — 401 (audience defect, see below)** |
| Tampered / forged+expired tokens rejected (401) | YES |
| `GET /v1/stats` against live `simplifyeu_db`, unmodified code | **401** (same defect) |
| `GET /v1/stats` against live `simplifyeu_db`, with 1-line aud fix | **200**, sane JSON |

**One real, deterministic, production-blocking bug was found** (audience claim) — details and fix below.
Everything else in the cross-language chain (key issuance → JWKS publication → EdDSA verification → `sub`
mapping → DB access scoped by team uuid) is proven correct.

---

## What was proven (the integration under test)

### STEP A — real Better Auth JWT + JWKS (same-process Node, `apps/web`)
- Imported the **real** `auth` instance from `apps/web/src/lib/auth.ts` via `tsx`, loading
  `apps/web/.env.local` (so `DATABASE_URL` = the live pooler URL to `simplifyeu_db`).
- `auth.api.signUpEmail(...)` created a fresh user; `auth.api.getToken(...)` minted a JWT; `auth.api.getJwks()`
  dumped the public key set. All same-process (no `next dev`, no cross-process HTTP).
- The signup **persisted to the live DB**: a `user` row (uuid id), the app `users` profile-mirror row with the
  SAME id (the `databaseHooks.user.create.after` hook works against `simplifyeu_db`), and a `jwks` key row
  (table went 0 → 1).
- Minted JWT claims: `sub` == `id` == user uuid; plus `iat`, `exp`, `iss=http://localhost:3000`,
  `aud=http://localhost:3000`. JWKS: 1 key, `alg=EdDSA`, `kty=OKP`, `crv=Ed25519`, has `kid`.

### STEP B — Python validates the real token (`services/team-reminder-bot`)
- Served the exported JWKS on a localhost port (thread), set `BETTER_AUTH_JWKS_URL` to it, imported the
  service's **real** `verify_jwt` from `src/auth/jwt_auth.py`, ran with `ENVIRONMENT=production` (no dev test-key bypass).
- **Trust chain is correct in isolation:** `PyJWKClient.get_signing_key_from_jwt` resolved the key by `kid`, and
  `jwt.decode(..., algorithms=["EdDSA"], verify_aud=False)` ACCEPTED the token with `sub` == the test user uuid.
- **But the service's real `verify_jwt` REJECTED the token → HTTP 401 "Invalid token".** Root cause below.
- Reject paths verified: tampered signature → 401; forged token re-signed with an attacker Ed25519 key (reusing
  the real `kid`) and an expired `exp` → 401.

### STEP C — service endpoint against the live `simplifyeu_db`
- FastAPI `TestClient` on `services/team-reminder-bot`'s `src.main:app`, with
  `app.dependency_overrides[get_db]` → a real SQLAlchemy `Session` to `simplifyeu_db` (pooler URL),
  `SERVICE_API_KEY` configured, `ENVIRONMENT=production`.
- Created a throwaway `teams` row (real write) to scope `/v1/stats`, sent
  `Authorization: Bearer <real JWT>`, `X-API-Key: <service key>`, `X-Account-ID: <team uuid>`.
- **PASS 1 (unmodified code): 401** — same audience defect as STEP B, end-to-end through the app.
- **PASS 2 (1-line aud fix applied at runtime via monkeypatch, NOT a source edit): 200**, body
  `{"status":"ok","data":{"total":0,"pending":0,...}}` — full chain works against the live DB; the negative
  control (tampered bearer) still returned 401.
- The throwaway team row was deleted; afterwards the test user + its `users`/`session`/`account` rows (FK
  cascade) and the `jwks` row were removed, restoring the DB to its pre-test state.

---

## THE BUG (must be fixed before Phase 7 cutover)

**`services/<svc>/src/auth/jwt_auth.py :: verify_jwt` rejects every real Better Auth token with `InvalidAudienceError` → HTTP 401.**

- Better Auth's `jwt()` plugin **always** stamps `aud` = the app's `baseURL` origin (here `http://localhost:3000`);
  confirmed in `better-auth/dist/plugins/jwt/sign.mjs` (`.setAudience(aud ?? defaultAud)` where
  `defaultAud = baseURLOrigin`). There is no real token without an `aud` claim unless `jwt.audience` is configured,
  and `apps/web/src/lib/auth.ts` does not configure it.
- PyJWT defaults to `verify_aud=True`. Its documented rule: *if the token has an `aud` claim but the caller passes
  no `audience=`, validation FAILS.* The service's `jwt.decode(...)` passes neither `audience=` nor `verify_aud=False`,
  so every BA token is rejected on the audience check — even though the EdDSA signature is valid.
- This is **deterministic and affects every service that uses this validator** (the file is described as the reusable
  validator copied across services). It is not a test artifact: it was isolated by showing `verify_aud=False` makes
  the exact same decode succeed.

**Fix (one of):**
1. Pass the expected audience in `jwt.decode`, e.g. `audience=settings.BETTER_AUTH_URL` (add a
   `BETTER_AUTH_URL`/`JWT_AUDIENCE` setting), **or**
2. Disable the audience check: add `"verify_aud": False` to the `options` dict in `verify_jwt`.

Option 1 is stronger (validates audience); option 2 is the minimal unblock. Apply to **every** service's
`jwt_auth.py`, not just team-reminder-bot. (PASS 2 above proved option-style fix yields 200 end-to-end.)

> Note: `iss` is NOT checked by the service today (only `exp` + `sub` are required). If you want issuer pinning at
> cutover, also pass `issuer=` — optional, not a blocker.

---

## Phase 7 cutover checklist (concrete, per component)

### 0. Fix the audience defect (blocker)
- [ ] Patch `verify_jwt` in **each** service's `src/auth/jwt_auth.py` (team-reminder-bot, subscription-analyzer,
      invoice-detector, crewai-agents — whichever use the BA JWT validator). Add the chosen aud handling above.
- [ ] Regenerate/rebuild service images (source is **not** bind-mounted in production compose; see step 4).

### 1. Web (`apps/web`)
- [ ] `DATABASE_URL` → `simplifyeu_db`. In-container it should point at the DB host reachable from the web
      container (see networking, step 5). The working value used in verification is the host pooler URL
      `postgresql://simplifyeu.hetzner-vps-tenant:<pw>@127.0.0.1:5432/simplifyeu_db` (tenant-qualified username
      required by supavisor). For a containerized web service use either the `supabase_default` DB host or the
      pooler reachable from that container — NOT `127.0.0.1` (that resolves to the container itself).
- [ ] `BETTER_AUTH_URL` (and `NEXT_PUBLIC_BETTER_AUTH_URL`) → the real public origin. **This origin becomes the JWT
      `iss` AND `aud`** — it must match whatever the services validate (tie to step 0 option 1).
- [ ] `BETTER_AUTH_SECRET` → the production secret (encrypts the JWKS private key; must be stable or the existing
      `jwks` rows can't be decrypted).
- [ ] Confirm the `jwks` table is migrated/present in `simplifyeu_db` (it is; auto-populated on first token mint).

### 2. Each Python service (`services/*`)
- [ ] `DATABASE_URL` → `simplifyeu_db` (libpq URL; the service auto-adds the `+psycopg` driver). Use the DB host
      reachable from the service container (step 5).
- [ ] `BETTER_AUTH_JWKS_URL` → the web app's public `…/api/auth/jwks` (or an in-network URL the service container
      can reach — must be reachable at runtime; see "unverified" below).
- [ ] `SERVICE_API_KEY` → the shared service key; the web app must send the SAME value in `X-API-Key`. In
      `ENVIRONMENT=production` the `sk_test_*`/`demo-key` bypass is disabled, so this MUST be set on both sides or
      every call 403s.
- [ ] `ENVIRONMENT=production`, `CORS_ORIGINS` → the real web origin(s) (prod default is restrictive/empty).
- [ ] Service-specific: `API_KEY_SALT`, Slack tokens (team-reminder-bot), LLM keys, Redis URL, SMTP, etc.

### 3. Remove the Supabase stack dependency for SimplifyEU
- [ ] `docker-compose.yml` and `docker-compose.production.yml` still inject `SUPABASE_URL`/`SUPABASE_KEY`/
      `SUPABASE_SERVICE_KEY` and only build `subscription-analyzer` (+ crewai). Replace those Supabase env vars with
      `DATABASE_URL` (+ `BETTER_AUTH_JWKS_URL`, `SERVICE_API_KEY`) for the Postgres-native services. Add compose
      entries for `team-reminder-bot` and any other migrated services (root compose lacks it today).
- [ ] Drop any code path / env still pointing at the Supabase REST/Auth API for these services.

### 4. Rebuild images (source is NOT bind-mounted in production)
- [ ] `docker-compose.production.yml` and the service `Dockerfile.production` `COPY . .` the source into the image —
      there is no bind mount in prod. So the audience fix (step 0) only takes effect after
      `docker compose -f docker-compose.production.yml build` (no `--scale`/restart shortcut).
- [ ] Note the root `docker-compose.yml` DOES bind-mount (`./services/...:/app`) for dev — fine for local, but prod
      must rebuild.
- [ ] Minor: `team-reminder-bot/Dockerfile.production` `EXPOSE 8001` / healthchecks `:8001`, but gunicorn/uvicorn
      default may differ — verify the listen port matches at cutover.

### 5. Container networking to Postgres
- [ ] `supabase-db` is on the `supabase_default` docker network and has **no host port** (only `5432/tcp`
      inside that network). `supabase-pooler` (supavisor) is also on `supabase_default` and publishes host ports
      `0.0.0.0:5432` (session) and `0.0.0.0:6543` (transaction).
- [ ] SimplifyEU app/services run on `simplifyeu_default` — they currently CANNOT resolve `supabase-db` by name.
      Choose one at cutover:
      - attach the SimplifyEU services to `supabase_default` (external network) and use the pooler/db hostname, **or**
      - reach the pooler via the Docker host gateway (`host.docker.internal` / the host bridge IP) on `:5432`, **or**
      - point services at the pooler's published host port from the host network.
- [ ] supavisor requires the **tenant-qualified username** `simplifyeu.hetzner-vps-tenant` — keep that in every
      `DATABASE_URL` that goes through the pooler (direct `supabase-db` connections use the plain `simplifyeu` user).

### 6. Lockfiles
- [ ] `pnpm-lock.yaml` is current (workspace uses pnpm). A stale `package-lock.json` is also present — remove it or
      ensure CI uses pnpm only, and regen `pnpm-lock.yaml` if any dep changed during the migration.

---

## What STILL REQUIRES a real live run (not provable in this verification env)

1. **The audience fix on a real built image** — verified here only via runtime monkeypatch + TestClient. A real
   `docker compose build` + `up` of the patched service, hit over real HTTP, is still required.
2. **Cross-container HTTP to the web's JWKS endpoint** — STEP A/B used the JWKS dumped same-process and served on
   localhost. In production the service's `PyJWKClient` fetches `BETTER_AUTH_JWKS_URL` over the network; that
   container→web reachability (DNS, TLS, the URL value) is unverified here.
3. **`iss`/`aud` values in the real deployment** — verification used `http://localhost:3000`. With the real
   `BETTER_AUTH_URL` the token's `iss`/`aud` change; confirm they match the service's audience config after the fix.
4. **Cross-process token mint via HTTP** (`/api/auth/sign-up-email` + `/api/auth/token` + `/api/auth/jwks` from a
   running `next` server) — only the same-process `auth.api` path was exercised.
5. **Containers reaching Postgres on the chosen networking option** (step 5) — verification connected from the host
   via the pooler; the in-container path was not exercised.
6. **The other services** (subscription-analyzer, invoice-detector, crewai-agents) — only team-reminder-bot was used
   as the representative service. They share the validator pattern, so the bug + fix should apply, but each still
   needs its own endpoint smoke test against `simplifyeu_db`.
7. **Real Slack / external integrations** for team-reminder-bot — out of scope here.

---

# Phase-7 CUTOVER — CONFIG PREP DONE (2026-06-21) + RUN CHECKLIST

## What was changed in the repo (branch `migrate/postgres`, NOT committed)

Compose files edited (all 3) — replaced `SUPABASE_URL`/`SUPABASE_KEY`/`SUPABASE_SERVICE_KEY`
in every service block with the vars the services actually read, and wired Postgres networking:

- `docker-compose.yml` (dev): `subscription-analyzer`, `crewai-agents`
- `docker-compose.production.yml`: `api`, `celery-worker` (both = subscription-analyzer;
  `celery-beat` & `redis` untouched — they never used Supabase)
- `docker-compose.traefik.yml`: `subscription-analyzer`, `crewai-agents`, `invoice-detector`,
  `team-reminder-bot`

New env per Python service block:
  `DATABASE_URL=${DATABASE_URL}`, `BETTER_AUTH_JWKS_URL=${BETTER_AUTH_JWKS_URL}`,
  `SERVICE_API_KEY=${SERVICE_API_KEY}`
All other env (LLM keys, REDIS_URL, API_KEY_SALT, CORS_ORIGINS, SMTP, Slack, Twilio) left untouched.
NOTE: the web (Next.js) app is NOT in any compose file — it runs on Vercel
(`apps/web/.env.local` / Vercel env: DATABASE_URL, BETTER_AUTH_URL, BETTER_AUTH_SECRET,
NEXT_PUBLIC_BETTER_AUTH_URL). So no "web service" compose edit was needed.

Other config:
- Removed stale `package-lock.json` (`git rm`, staged not committed). Repo lockfile is `pnpm-lock.yaml`.
- Created root `.env.example` (non-secret placeholders) documenting every var the compose files
  now expect. Real `.env` / `.env.local` / `.env.postgres` remain gitignored.

## Networking choice (APPLIED): pooler via Docker host gateway

Chosen because it needs the LEAST infra change: the supavisor pooler ALREADY publishes
`0.0.0.0:5432` (session) and `0.0.0.0:6543` (transaction) on the host, and the web app already
proved this exact credential form works from the host. So each service block got:

    extra_hosts:
      - "host.docker.internal:host-gateway"

and `DATABASE_URL` reaches the pooler through the host gateway. No attachment to
`supabase_default`, no change to the supabase stack or way2buy.

Resulting DATABASE_URL form (tenant-qualified user required by supavisor):

    postgresql://simplifyeu.hetzner-vps-tenant:<DB_PASSWORD>@host.docker.internal:5432/simplifyeu_db
    (transaction pooler alternative: swap :5432 -> :6543)

ALTERNATIVE (flagged, NOT applied): attach each SimplifyEU service to the external
`supabase_default` network and use `DATABASE_URL=...@supabase-db:5432/...` with the PLAIN
`simplifyeu` role (direct, no tenant suffix). Viable but entangles SimplifyEU with the supabase
network and bypasses the pooler — only switch if the host-gateway path proves unreliable.

## Verification done in config-prep env (no build/up)
- `grep -rn SUPABASE docker-compose*.yml` -> EMPTY (exit 1). 
- `python3 -c "import yaml; yaml.safe_load(...)"` -> all 3 YAML OK.
- `docker compose --env-file <dummy> -f <each> config -q` -> PARSE OK for all 3 (only the benign
  obsolete-`version` warning; left as-is to keep the diff surgical).
- Resolved config confirms `extra_hosts: host.docker.internal=host-gateway` + the 3 new env vars
  render, and no SUPABASE remains.

## ============ PHASE-7 RUN CHECKLIST (execute on the VPS at cutover) ============

# 0. Prereqs
#    - Real root `.env` present (gitignored) with: DATABASE_URL (host-gateway pooler form above),
#      BETTER_AUTH_JWKS_URL (web's public /api/auth/jwks), SERVICE_API_KEY (SAME value the web sends
#      in X-API-Key), + existing LLM/REDIS/SMTP/Slack/Twilio/API_KEY_SALT/CORS_ORIGINS.
#    - SERVICE_API_KEY MUST match the web side or every call 403s under ENVIRONMENT=production.

# 1. Regenerate the web lockfile (package-lock.json removed; web's pnpm-lock still lists removed
#    @supabase deps).
cd /srv/sergiy_prod/SimplifyEU
pnpm install            # regenerates pnpm-lock.yaml without @supabase/*

# 2. Apply DB migrations IF simplifyeu_db is fresh (idempotent files; skip if already applied).
#    Connect via the host pooler with the tenant-qualified user (same creds as web .env.local):
for m in 0001_app_schema 0002_better_auth 0003_jwt; do
  psql "postgresql://simplifyeu.hetzner-vps-tenant:<DB_PASSWORD>@127.0.0.1:5432/simplifyeu_db" \
    -v ON_ERROR_STOP=1 -f db/migrations/$m.sql
done
#    (verify: \dt shows app tables + better-auth `user/session/account/verification` + jwt `jwks`.)

# 3. Build images (prod COPYs source — no bind mount; must rebuild, not just restart).
docker compose -f docker-compose.traefik.yml build        # prod-on-VPS path (traefik)
#    or for the simple/dev compose:
#    docker compose -f docker-compose.yml build
#    or the gunicorn/celery prod stack:
#    docker compose -f docker-compose.production.yml build

# 4. Bring services up.
docker compose -f docker-compose.traefik.yml up -d
docker compose -f docker-compose.traefik.yml ps           # all Up/healthy

# 5. E2E smoke (register -> login -> a service call).
#    a) Web auth (mints JWT via Better Auth). Against the deployed web origin:
curl -sS -X POST https://simplify-eu.vercel.app/api/auth/sign-up/email \
  -H 'Content-Type: application/json' \
  -d '{"email":"smoke+p7@example.com","password":"Sm0ke-Test-Pass!","name":"P7"}'
#    b) Login (get session) then mint a JWT:
curl -sS -X POST https://simplify-eu.vercel.app/api/auth/sign-in/email \
  -H 'Content-Type: application/json' -c /tmp/p7.cookies \
  -d '{"email":"smoke+p7@example.com","password":"Sm0ke-Test-Pass!"}'
TOKEN=$(curl -sS https://simplify-eu.vercel.app/api/auth/token -b /tmp/p7.cookies | jq -r .token)
#    c) Call a Python service with the JWT + the shared service key:
curl -sS https://api.smiro.dev/health
curl -sS -H "Authorization: Bearer $TOKEN" -H "X-API-Key: $SERVICE_API_KEY" \
  https://api.smiro.dev/<an-authed-endpoint>     # expect 200, not 401/403
#    Repeat (c) per service: api/agents/invoices/reminders.smiro.dev.

# 6. What to WATCH / likely failure points
#    - DB connect: if services can't reach Postgres, confirm `host.docker.internal` resolves inside
#      the container (`docker exec <svc> getent hosts host.docker.internal`) and that the pooler is
#      listening on the host :5432. If host-gateway is unreliable, fall back to the ALTERNATIVE
#      (attach to supabase_default + supabase-db:5432 + plain `simplifyeu` role).
#    - supavisor auth: the username MUST stay tenant-qualified (simplifyeu.hetzner-vps-tenant) for
#      the pooler path; a plain `simplifyeu` user only works on a DIRECT supabase-db connection.
#    - JWT verify: 401 => service can't fetch BETTER_AUTH_JWKS_URL from inside the container, or
#      iss/aud mismatch (token iss/aud follow the real BETTER_AUTH_URL, not localhost). Check the
#      service can curl the JWKS URL from within the container.
#    - 403 on authed calls => SERVICE_API_KEY mismatch between web and service (prod disables the
#      sk_test_/demo-key bypass).
#    - Rebuild gotcha: code/audience fixes only take effect after `build`; `restart` is not enough
#      for the prod/traefik images (they COPY source, no bind mount).
#    - Do NOT disturb the supabase stack or way2buy while bringing this up.

# 7. ROLLBACK (reversible): `git checkout -- docker-compose*.yml`, `git restore --staged package-lock.json
#    && git checkout -- package-lock.json`, `rm .env.example`. Compose still reads SUPABASE_* again.
