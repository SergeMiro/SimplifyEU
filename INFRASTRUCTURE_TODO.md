# 🏗️ Infrastructure TODO - Платные компоненты для Production

> Этот файл содержит список компонентов, которые нужно установить/настроить 
> для полноценного production deployment с поддержкой 10,000+ concurrent users.

---

## ⚠️ Статус: НЕ УСТАНОВЛЕНО (требует оплаты)

### 1. 🔴 Redis (обязательно для Celery)

**Зачем нужен:** Background task queue (Celery), LLM response caching, rate limiting storage

**Варианты:**

| Провайдер | Free Tier | Production | Цена |
|-----------|-----------|------------|------|
| [Upstash](https://upstash.com) | 10K cmd/day | Unlimited | $0 → $10+/месяц |
| [Redis Cloud](https://redis.io/cloud/) | 30MB | Scalable | $0 → $7+/месяц |
| Self-hosted | ∞ | ∞ | VPS cost |

**Настройка после покупки:**
```bash
# .env
REDIS_URL=redis://default:password@host:6379

# Или для Upstash
REDIS_URL=rediss://default:token@region.upstash.io:6379
```

**Команды для проверки:**
```bash
# Запустить Celery worker
celery -A src.celery_app worker --loglevel=info

# Мониторинг
celery -A src.celery_app flower
```

---

### 2. 🔴 Supabase Pro (для 10K+ connections)

**Зачем нужен:** Connection pooling upgrade, более высокие лимиты

**Текущий план:** Free
- ~60 pooled connections
- 500MB storage
- 2GB bandwidth

**Pro план ($25/месяц):**
- 200+ pooled connections
- 8GB storage
- 50GB bandwidth
- Daily backups

**Настройка Pooler (уже доступно в Free):**
```bash
# Вместо Direct URL
SUPABASE_URL=https://xxx.supabase.co

# Использовать Pooler URL для высокой нагрузки
# Dashboard → Settings → Database → Connection Pooling
# Mode: Transaction (рекомендуется)
```

---

### 3. 🔴 Production Hosting (VPS/Cloud)

**Зачем нужен:** Запуск multiple Gunicorn workers, Celery workers

**Минимальные требования для 10K:**
- 4 vCPU
- 8GB RAM
- SSD storage

**Варианты:**

| Провайдер | Specs | Цена |
|-----------|-------|------|
| [Hetzner](https://hetzner.com) | CX31 (4vCPU/8GB) | €8.21/месяц |
| [Contabo](https://contabo.com) | VPS M (6vCPU/16GB) | €8.99/месяц |
| [DigitalOcean](https://digitalocean.com) | Basic (4vCPU/8GB) | $48/месяц |
| [Railway](https://railway.app) | Auto-scale | Pay per use |

**Docker Compose для production:**
```yaml
# См. docker-compose.production.yml в корне проекта
```

---

### 4. 🟡 Monitoring (опционально, но рекомендуется)

**Варианты:**

| Сервис | Free Tier | Цена |
|--------|-----------|------|
| [Sentry](https://sentry.io) | 5K errors/month | $0 → $26/месяц |
| [Grafana Cloud](https://grafana.com) | 10K metrics | $0 |
| [Better Stack](https://betterstack.com) | Logs + Uptime | $0 → $25/месяц |

---

## ✅ УЖЕ УСТАНОВЛЕНО (бесплатно)

| Компонент | Статус | Файл |
|-----------|--------|------|
| Celery (код) | ✅ | `src/celery_app.py`, `src/tasks/` |
| Gunicorn config | ✅ | `gunicorn.conf.py` |
| LLM Caching (код) | ✅ | `src/core/cache.py` |
| Rate Limiting | ✅ | `src/main.py` (slowapi) |
| Security fixes | ✅ | CORS, Auth, Logging |

---

## 📋 Checklist перед Production

- [ ] Купить/настроить Redis (Upstash или self-hosted)
- [ ] Настроить Supabase Pooler URL
- [ ] Арендовать VPS (Hetzner рекомендуется)
- [ ] Настроить SSL сертификаты
- [ ] Настроить CORS_ORIGINS для production домена
- [ ] Установить ENVIRONMENT=production
- [ ] Настроить API_KEY_SALT
- [ ] Настроить SMTP для email отчётов
- [ ] Добавить мониторинг (Sentry)
- [ ] Настроить автоматические бэкапы

---

## 💡 Быстрый старт (после покупки Redis)

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Настроить .env
cp .env.example .env
# Добавить REDIS_URL

# 3. Запустить API (4 workers)
gunicorn -c gunicorn.conf.py src.main:app

# 4. Запустить Celery workers (в отдельном терминале)
celery -A src.celery_app worker --loglevel=info --concurrency=4

# 5. Запустить Celery beat для scheduled tasks (опционально)
celery -A src.celery_app beat --loglevel=info
```

---

*Последнее обновление: 2026-02-03*
