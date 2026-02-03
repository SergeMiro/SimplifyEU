"""
Celery application configuration.

This module sets up Celery for background task processing.
Currently configured to work WITHOUT Redis (in-memory) for development.
For production, set REDIS_URL environment variable.
"""
import os
from celery import Celery

# Redis URL (optional - falls back to eager mode without it)
REDIS_URL = os.getenv("REDIS_URL")

# Celery configuration
if REDIS_URL:
    # Production mode with Redis
    celery_app = Celery(
        "subscription_analyzer",
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=["src.tasks.analysis_tasks"]
    )
else:
    # Development mode - tasks run synchronously
    celery_app = Celery(
        "subscription_analyzer",
        broker="memory://",
        backend="cache+memory://",
        include=["src.tasks.analysis_tasks"]
    )
    # Run tasks immediately in development
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="Europe/Paris",
    enable_utc=True,
    
    # Task settings
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit 9 minutes
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Fair task distribution
    worker_concurrency=4,  # Number of worker processes
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Retry settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    
    # Rate limiting (per worker)
    task_default_rate_limit="100/m",
)

# Task routes for different queues
celery_app.conf.task_routes = {
    "src.tasks.analysis_tasks.run_analysis": {"queue": "analysis"},
    "src.tasks.analysis_tasks.send_email_report": {"queue": "email"},
    "src.tasks.analysis_tasks.cleanup_old_analyses": {"queue": "maintenance"},
}

# Scheduled tasks (requires celery beat)
celery_app.conf.beat_schedule = {
    "cleanup-old-analyses": {
        "task": "src.tasks.analysis_tasks.cleanup_old_analyses",
        "schedule": 86400.0,  # Daily
    },
}
