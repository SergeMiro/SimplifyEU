# Gunicorn configuration for Team Reminder Bot
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8001"

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 4)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Timeout
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "team-reminder-bot"

# Preload app for faster worker startup
preload_app = True

# Max requests per worker before restart (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50
