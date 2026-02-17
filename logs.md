2026-01-30 21:55 | scope=repo | change=modified | files=tsconfig.json |
purpose=started dev server and verified listening on port 3000 | tests=pnpm dev
2026-01-30 22:15 | scope=service/subscription-analyzer | change=none |
files=none | purpose=started python service manually | tests=curl
localhost:8001/docs 2026-01-31 11:30 | scope=apps/web | change=created |
files=app/ai-test/page.tsx,app/api/ai-test/route.ts,app/page.tsx | purpose=added
AI test interface with Chutes API integration | tests=none 2026-01-31 11:45 |
scope=apps/web | change=created | files=app/dashboard/page.tsx |
purpose=dashboard page with service cards | tests=pnpm dev 2026-01-31 12:30 |
scope=services/subscription-analyzer | change=created |
files=test*data/generate_test_data.py,test_data/*.csv,test*data/*.xlsx,core/csv*parser.py
| purpose=synthetic test data generator + Excel support | tests=pytest |
notes=240 transactions generated 2026-01-31 12:49 | scope=repo | change=created
| files=TESTING_GUIDE.md | purpose=central microservices testing guide |
tests=N/A 2026-01-31 12:52 | scope=repo | change=modified |
files=TESTING_GUIDE.md,.github/workflows/test-services.yml | purpose=added
manual API tests and GitHub Actions CI | tests=pytest 2026-01-31 13:15 |
scope=services/subscription-analyzer | change=modified |
files=tests/*,test*data/* | purpose=restructured tests: moved test*data inside
tests folder for better logic 2026-01-31 13:21 |
scope=services/subscription-analyzer | change=modified |
files=tests/test_data/.gitkeep | purpose=ensure test_data folder structure is
preserved | tests=pytest 2026-01-31 13:40 | scope=repo | change=modified |
files=apps/web/src/app/dashboard/services/subscription-detector/page.tsx,
services/subscription-analyzer/src/api/v1/analyses.py | purpose=added dark mode,
upgrade btn, clean delete logic | tests=manual verify in browser 2026-01-31
13:35 | scope=services/subscription-analyzer | change=created,modified |
files=src/core/email_service.py,src/config.py,src/api/v1/analyses.py,.env.example,tests/test_email_service.py
| purpose=implemented email report sending via SMTP with HTML templates |
tests=pytest (20 passed) 2026-01-31 14:30 | scope=services/subscription-analyzer
| change=created,modified |
files=src/core/pdf_parser.py,src/api/v1/analyses.py,tests/test_pdf_parser.py,requirements.txt
| purpose=implemented PDF parsing with OCR support, added /capabilities endpoint
| tests=pytest 2026-01-31 14:45 | scope=apps/web | change=modified |
files=src/components/file-upload.tsx,src/app/dashboard/services/subscription-detector/page.tsx,src/app/dashboard/services/subscription-detector/[analysisId]/page.tsx
| purpose=refactored dashboard dark mode, added email modal, PDF format badges,
improved UX | tests=manual 2026-01-31 15:25 | scope=repo | change=none |
files=supabase/migrations/quick_setup.sql | purpose=detected missing Supabase
MCP access, provided manual SQL migration script | tests=N/A 2026-01-31 15:50 |
scope=service/subscription-analyzer | change=modified |
files=src/auth/api_key.py | purpose=fixed auth middleware hanging on demo keys
by moving dev check before DB query | tests=curl verified working 2026-01-31
20:53 | scope=repo | change=modified |
files=apps/web/.env.local,apps/web/src/\*/page.tsx,services/subscription-analyzer/src/api/v1/analyses.py
| purpose=fixed Failed to fetch error: changed API URL from 127.0.0.1 to
localhost, made X-User-ID header optional | tests=curl verified 2026-01-31 21:33
| scope=services/subscription-analyzer | change=created,modified |
files=src/core/ocr.py,src/core/pdf_parser.py,requirements.txt,tests/test_ocr.py,tests/test_pdf_parser.py
| purpose=upgraded OCR from Tesseract to PaddleOCR for 109-language support and
table detection | tests=pytest (50 passed, 1 skipped) 2026-02-03 11:37 |
scope=repo | change=created | files=SECURITY_PERFORMANCE_REPORT.md |
purpose=full security audit + 10K load analysis: identified CORS/auth-bypass/RLS
critical issues, performance bottlenecks, scaling recommendations | tests=pytest
(50 passed) 2026-02-03 14:55 | scope=services/subscription-analyzer |
change=modified,created |
files=src/main.py,src/auth/api_key.py,src/config.py,src/api/v1/analyses.py,requirements.txt,tests/test_security.py
| purpose=Option B security fixes: CORS hardening, auth bypass blocked in prod,
rate limiting, no API key logging, production safety checks | tests=pytest (59
passed), semgrep security-audit+owasp-top-ten (0 findings) 2026-02-03 15:40 |
scope=services/subscription-analyzer,repo | change=created |
files=src/celery_app.py,src/tasks/analysis_tasks.py,src/core/cache.py,src/core/classifier.py,gunicorn.conf.py,Dockerfile.production,docker-compose.production.yml,INFRASTRUCTURE_TODO.md
| purpose=Option C free components: Celery for background tasks, Gunicorn
multi-worker config, LLM response caching with Redis fallback | tests=pytest (59
passed) 2026-02-14 12:08 | scope=apps/web | change=modified | files=.env.local |
purpose=update Supabase anon key to new publishable format to fix fetch error |
tests=manual login verification needed 2026-02-14 13:10 | scope=apps/web |
change=created |
files=src/i18n/*,messages/\_,src/middleware.ts,next.config.mjs,src/components/language-switcher.tsx
| purpose=installed next-intl for i18n (EN, FR, ES) | tests=manual 2026-02-17
16:30 | scope=services/team-reminder-bot | change=created |
files=src/**/\*,tests/**/_,Dockerfile,Dockerfile.production,gunicorn.conf.py,requirements.txt,README.md,.env.example,supabase/migrations/20260217_team_reminder_bot.sql
| purpose=new Team Reminder Bot microservice: NLP time parsing, Slack Block Kit,
context-aware reminders, background queue worker | tests=pytest (4 test files)
2026-02-17 16:45 | scope=services/invoice-detector | change=created |
files=src/\*\*/_,tests/\*_/_,Dockerfile,Dockerfile.production,gunicorn.conf.py,requirements.txt,README.md,.env.example,supabase/migrations/20260217_invoice_detector.sql
| purpose=new Invoice Duplicate Detector microservice: PDF/OCR extraction,
multi-language invoice parsing, weighted fuzzy similarity scoring | tests=pytest
(4 test files)
