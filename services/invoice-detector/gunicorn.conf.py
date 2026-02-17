# Gunicorn configuration for Invoice Duplicate Detector
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8002"

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 4)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Timeout (longer for OCR processing)
timeout = 300
keepalive = 5
graceful_timeout = 60

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "invoice-detector"

# Preload
preload_app = True

# Max requests per worker  (prevents memory leaks from PDF/OCR)
max_requests = 500
max_requests_jitter = 50
