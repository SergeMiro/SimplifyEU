# Team Reminder Bot

Intelligent reminder microservice with context-aware notifications for
Slack/Teams.

## Architecture

```
src/
├── main.py              # FastAPI app entry point
├── config.py            # Pydantic settings
├── api/v1/
│   ├── reminders.py     # Reminder CRUD + snooze + queue trigger
│   └── teams.py         # Team registration
├── auth/
│   └── api_key.py       # API key authentication (bcrypt)
├── core/
│   ├── time_parser.py      # Natural language time parsing (EN/RU)
│   ├── reminder_scheduler.py # CRUD + scheduling + recurring
│   ├── context_manager.py   # Event logging + user stats + related tasks
│   ├── slack_formatter.py   # Slack Block Kit message generation
│   └── queue_worker.py      # Background poller for due reminders
├── db/
│   ├── client.py        # Supabase singleton
│   └── models.py        # Pydantic models
└── utils/
    └── logger.py        # Structured logging
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your Supabase and Slack credentials

# Run in development
uvicorn src.main:app --reload --port 8001

# Run tests
python -m pytest tests/ -v
```

## API Endpoints

| Method | Path                        | Description                |
| ------ | --------------------------- | -------------------------- |
| GET    | `/health`                   | Health check               |
| POST   | `/v1/reminders`             | Create reminder            |
| GET    | `/v1/reminders`             | List reminders (paginated) |
| GET    | `/v1/reminders/{id}`        | Get single reminder        |
| PATCH  | `/v1/reminders/{id}`        | Update reminder            |
| DELETE | `/v1/reminders/{id}`        | Delete reminder            |
| POST   | `/v1/reminders/{id}/snooze` | Snooze reminder            |
| POST   | `/v1/teams`                 | Register team              |
| GET    | `/v1/teams/{id}`            | Get team details           |
| GET    | `/v1/stats`                 | Team statistics            |

## Auth

All `/v1/*` endpoints require:

- `X-API-Key` header (bcrypt validated)
- `X-Account-ID` header

In development, `sk_test_*` keys are accepted.
