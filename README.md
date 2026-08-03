# SimplifyEU

**Administrative overhead for EU companies, handled by four small Python services instead of
one large application:** duplicate invoices, forgotten subscriptions, a crew of AI
assistants, and the deadline reminders nobody wants to send.

[![Next.js](https://img.shields.io/badge/Next.js-16.1-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-4_services-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![CrewAI](https://img.shields.io/badge/CrewAI-5_agents-FF5A50)](https://www.crewai.com/)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres%20%C2%B7%20Auth-3FCF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![Celery](https://img.shields.io/badge/Celery-background_jobs-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Turborepo](https://img.shields.io/badge/Turborepo-pnpm_workspace-EF4444?logo=turborepo&logoColor=white)](https://turbo.build/)
[![Docker](https://img.shields.io/badge/Docker-Traefik-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🌐 **Demo:** [simplify-eu.vercel.app](https://simplify-eu.vercel.app) — the marketing side is
open; the dashboard needs an account.

---

## Table of contents

- [Overview](#overview)
- [The services](#the-services)
- [Complete tech stack](#complete-tech-stack)
- [Architecture](#architecture)
- [Data model](#data-model)
- [Getting started](#getting-started)
- [Commands](#commands)
- [Deployment](#deployment)
- [Repository layout](#repository-layout)
- [Security](#security)
- [License](#license)

## Overview

SimplifyEU targets the administrative work a small European company cannot avoid: invoicing
with the right VAT treatment, subscriptions that quietly renew, filings with deadlines, and
documents nobody has time to read.

The design choice that shapes the repository: **one thin web surface, four independent
Python services.** The Next.js app is the only thing a user talks to; each service owns one
problem, has its own Dockerfile, its own Supabase migration and its own API key. Nothing is
shared except types in `packages/shared` and the database.

Everything is localised in **three languages** (English, French, Spanish) with the locale in
the route segment.

## The services

### Web application — `apps/web`

The one surface a user sees: locale-prefixed routes, Supabase sign-in, and a dashboard that
fans out to whichever service answers the question.

- **Next.js 16 App Router** with `[locale]` segments — every page exists per language by
  construction
- **Supabase SSR client** — the session is read on the server, never trusted from the client
- **Tailwind CSS 4 + Radix UI** — mobile-first, with a bottom navigation bar on small screens
- **Stripe** for subscription billing, **Recharts** for the dashboard, **next-themes** for
  dark mode, **sonner** for toasts, **cmdk** for the command palette
- `react-hook-form` + **Zod** on every form; `/ai-test` verifies the AI integrations

### Invoice duplicate detector — `services/invoice-detector`

The same invoice paid twice is a common and expensive accident. This service reads the PDFs,
falls back to OCR when there is no text layer, and matches on fuzzy similarity rather than
exact fields.

- **pdfplumber** + **PyPDF2** for text and table extraction
- **pytesseract** + **Pillow** fallback, so a scanned invoice still gets read
- **python-magic** for real content-type detection on upload
- **fuzzywuzzy** + **python-Levenshtein** — `INV-2026/12` and `INV 2026 12` are the same document
- **slowapi** rate limiting, so an upload endpoint cannot be used as a grinder
- Results stored as `invoices` and `duplicate_pairs`

### Subscription analyser — `services/subscription-analyzer`

Feed it a bank export and it reports what recurs, what rose in price and what nobody uses —
then sends the finding as a PDF.

- **Celery** workers, so a long analysis runs off the request path
- **pandas** for the tabular analysis; CSV, PDF (**pdfplumber**, **pdf2image**) and OCR
  through the same pipeline
- **PaddleOCR** + **paddlepaddle** for scanned statements
- Recurrence classifier and price-rise detector kept deliberately separate
- **Redis** cache — re-running the same file is free
- **reportlab** / **openpyxl** to emit the PDF and spreadsheet reports

### CrewAI assistants — `services/crewai-agents`

Five specialised agents rather than one prompt asked to be all five, each with its own
agent, crew and flow:

| Agent | Scope |
| --- | --- |
| `financial_assistant` | Cash, invoices, financial insights |
| `tax_assistant` | VAT and tax obligations |
| `document_manager` | Document classification and linking |
| `operations_coordinator` | Internal operations |
| `client_assistant` | Client-facing answers |

- **CrewAI** + **crewai-tools** — roles, tasks and hand-off between agents
- **FastAPI** + **gunicorn** — each crew is reachable as a plain HTTP service
- **APScheduler** for recurring runs, **Twilio** for notifications, **Redis** for caching
- **reportlab** / **openpyxl** for generated documents
- API-key auth per service — the web app is the only legitimate caller
- Execution recorded in `agent_execution_logs`, configurable via `agent_settings`

### Team reminder bot — `services/team-reminder-bot`

Deadlines a small company keeps missing — filings, renewals, payments — chased automatically
instead of depending on who remembers.

- Teams and reminders API: who is reminded, of what, and how often
- **dateparser** + **python-dateutil** for human deadline expressions
- Supabase as the store, with its own migration

## Complete tech stack

**Monorepo** — pnpm workspaces (`apps/*`, `packages/*`, `services/*`) · Turborepo 2 ·
TypeScript 5.6 · Prettier + `prettier-plugin-tailwindcss` · ESLint · Node.js 20+

**Frontend** — Next.js 16.1 (App Router, `[locale]` routing) · React 19.2 · Tailwind CSS 4
(`@tailwindcss/postcss`, `tailwindcss-animate`) · Radix UI (16 primitives) · Lucide React ·
`class-variance-authority` · `clsx` · `tailwind-merge` · next-intl 4 · next-themes · sonner ·
cmdk · react-day-picker · date-fns · Recharts · react-hook-form + `@hookform/resolvers` · Zod

**Backend services (Python)** — FastAPI · Uvicorn · Gunicorn · Pydantic v2 +
pydantic-settings · httpx · slowapi (rate limiting) · passlib[bcrypt] · python-multipart ·
python-dotenv

**AI & agents** — CrewAI · crewai-tools · five specialised agents/crews/flows

**Document & data processing** — pdfplumber · PyPDF2 · pdf2image · python-magic ·
pytesseract · PaddleOCR + paddlepaddle · Pillow · pandas · openpyxl · reportlab ·
fuzzywuzzy + python-Levenshtein · dateparser · python-dateutil

**Data & auth** — Supabase (Postgres, Auth, Storage) · `@supabase/supabase-js` ·
`@supabase/ssr` · Python `supabase` client · 7 dated SQL migrations · API keys per service

**Payments** — Stripe 17

**Background work** — Celery · APScheduler · Redis

**Notifications** — Twilio

**Testing** — Jest + Testing Library (web) · Playwright (e2e) · pytest + pytest-asyncio +
pytest-cov (services)

**Infrastructure** — Docker · Docker Compose (dev, production, Traefik) · Traefik ·
Vercel (web) · GitHub Actions · opengrep (static security scanning, run out of band)

## Architecture

```
                      browser  (en · fr · es)
                          │
                          ▼
        ┌────────────────────────────────────────┐
        │  apps/web — Next.js 16 App Router      │
        │  [locale]/dashboard · auth · ai-test   │
        │  Supabase SSR session · Stripe billing │
        └───┬────────┬────────────┬─────────────┘
            │ API key per service
   ┌────────┴──┐  ┌──┴───────────┐  ┌──────┴───────┐  ┌──────────────┐
   │ invoice-  │  │ subscription-│  │ crewai-      │  │ team-        │
   │ detector  │  │ analyzer     │  │ agents       │  │ reminder-bot │
   │ FastAPI   │  │ FastAPI      │  │ FastAPI      │  │ FastAPI      │
   │ pdfplumber│  │ pandas       │  │ CrewAI ×5    │  │ dateparser   │
   │ pytesser. │  │ Celery+Redis │  │ APScheduler  │  │              │
   │ fuzzywuzzy│  │ PaddleOCR    │  │ Twilio       │  │              │
   └─────┬─────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         └───────────────┴─────────────────┴─────────────────┘
                                 │
                                 ▼
                    Supabase — Postgres + Auth + Storage
                    (one migration per service)
                                 │
                    packages/shared — types shared by app and services
```

Rules that hold it together:

- **The web app is the only caller.** Every service authenticates the caller with its own
  API key; none of them is meant to be reachable from a browser.
- **One migration per feature.** Services do not share tables by accident — each ships its
  own dated SQL migration.
- **Shared types, not shared code.** `packages/shared` exports types, utils and db helpers;
  everything else stays inside its own service.
- **Same shape locally and in production.** A Dockerfile per Python service, plus
  `docker-compose.yml`, `docker-compose.production.yml` and `docker-compose.traefik.yml`.

## Data model

25 tables in Supabase Postgres, added by seven dated migrations:

- **Identity & tenancy** — `users`, `accounts`, `teams`, `memberships`, `business_profiles`,
  `api_keys`
- **Billing & compliance** — `invoices`, `subscriptions`, `services`, `tax_obligations`
- **Invoice detection** — `duplicate_pairs`, `document_links`
- **Subscription analysis** — `analyses`, `analysis_items`, `financial_insights`,
  `weekly_reports`
- **Agents** — `agent_execution_logs`, `agent_settings`, `agent_notifications`,
  `context_history`
- **Reminders** — `reminders`, `notifications`
- **Platform** — `audit_logs`, `api_usage`, `webhook_logs`

## Getting started

### Prerequisites

- Node.js 20+ and pnpm 9.12+
- Python 3.11+ (one virtualenv per service)
- Docker (optional, for running everything together)
- A Supabase project
- Redis, if you run the subscription analyser or the agent cache

### Web application

```bash
pnpm install
pnpm dev              # turbo run dev → http://localhost:3000
```

### A Python service

```bash
cd services/invoice-detector
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

`invoice-detector` also needs Tesseract installed on the host for the OCR fallback; the
subscription analyser needs `poppler` for `pdf2image`.

### Database

Apply the migrations in `supabase/migrations/` in date order
(`supabase/migrations/quick_setup.sql` bootstraps a fresh project).

### Everything at once

```bash
docker compose up --build
```

## Commands

Run from the repository root — Turborepo fans each task out across the workspace.

| Command | What it does |
| --- | --- |
| `pnpm dev` | Development servers |
| `pnpm build` | Build every workspace |
| `pnpm lint` | Lint every workspace |
| `pnpm test` / `test:unit` / `test:e2e` | Jest, unit and Playwright suites |
| `pnpm format` | Prettier over `ts,tsx,md,json` |
| `pnpm db:generate` / `db:push` / `db:studio` | Supabase workflow |

Per-service Python tests: `pytest` inside the service directory (pytest-asyncio and
coverage are configured).

## Deployment

- **Web** — Vercel
- **Services** — one Docker image each; `docker-compose.production.yml` for the production
  set and `docker-compose.traefik.yml` for TLS termination and routing
- **CI** — GitHub Actions (`test-services.yml`): Python service tests plus `pnpm lint`
- Additional notes: [`INFRASTRUCTURE_TODO.md`](INFRASTRUCTURE_TODO.md),
  [`SECURITY_PERFORMANCE_REPORT.md`](SECURITY_PERFORMANCE_REPORT.md),
  [`TESTING_GUIDE.md`](TESTING_GUIDE.md)

## Repository layout

```
apps/
  web/                  Next.js 16 app — [locale] routes, auth, dashboard, ai-test
    src/app/[locale]/   auth (login, register, callback), dashboard, services
    src/components/ui/  Radix-based component library
    src/lib/supabase/   server and browser clients
    messages/           en · fr · es
packages/
  shared/               types, utils and db helpers shared by app and services
services/
  invoice-detector/     FastAPI · pdfplumber · pytesseract · fuzzywuzzy
  subscription-analyzer/ FastAPI · pandas · Celery · PaddleOCR · reportlab
  crewai-agents/        FastAPI · CrewAI — 5 agents / crews / flows, APScheduler, Twilio
  team-reminder-bot/    FastAPI · dateparser — teams and reminders
supabase/migrations/    7 dated migrations, one per feature
scripts/                operational scripts
docker-compose*.yml     dev · production · Traefik
turbo.json              task graph
```

## Security

- **API key per service**, verified on every request — the web app is the only intended caller
- **slowapi** rate limiting on the upload and analysis endpoints
- **passlib[bcrypt]** for credential hashing
- **python-magic** content-type verification on uploads, rather than trusting the extension
- Supabase session read server-side via `@supabase/ssr`; never trusted from the client
- `api_keys`, `api_usage`, `audit_logs` and `webhook_logs` make calls attributable
- **opengrep** static analysis, with findings tracked in `SECURITY_PERFORMANCE_REPORT.md`

## License

[MIT](LICENSE) © 2026 Mirochnyk

---

Built by **Sergiy Mirochnyk** · [smiro.dev](https://smiro.dev)
