"""
Gunicorn configuration for production deployment.

Run with:
    gunicorn -c gunicorn.conf.py src.main:app

For development, continue using uvicorn directly.
"""
import os
import multiprocessing

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker processes
#
# Recommended formula: (2 x CPU cores) + 1
# For I/O bound apps (like this one), can use more
# 
# Examples:
#   - 2 core VPS: 5 workers
#   - 4 core VPS: 9 workers
#   - 8 core VPS: 17 workers
#
workers = int(os.getenv("GUNICORN_WORKERS", (multiprocessing.cpu_count() * 2) + 1))

# Worker class - use uvicorn for async support
worker_class = "uvicorn.workers.UvicornWorker"

# Threads per worker (for sync workers, not used with UvicornWorker)
threads = 1

# Maximum requests per worker before restart (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50  # Random jitter to prevent all workers restarting at once

# Timeout settings
timeout = 120  # Worker timeout in seconds
graceful_timeout = 30  # Time to finish serving requests on restart
keepalive = 5  # Keep-alive connections timeout

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # stdout
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")  # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "subscription-analyzer"

# Server mechanics
daemon = False  # Don't daemonize (for Docker)
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment if using SSL directly, otherwise use reverse proxy)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

# Preload app for faster worker startup and shared memory
# IMPORTANT: Disable if using in-memory state that shouldn't be shared
preload_app = True

# Worker lifecycle hooks
def on_starting(server):
    """Called before the master process is initialized."""
    pass


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    pass


def when_ready(server):
    """Called just after the server is started."""
    print(f"[GUNICORN] Server is ready. Listening on {bind}")
    print(f"[GUNICORN] Workers: {workers}, Worker class: {worker_class}")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"[GUNICORN] Worker {worker.pid} spawned")


def pre_exec(server):
    """Called just before a new master process is forked."""
    pass


def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    print(f"[GUNICORN] Worker {worker.pid} received interrupt")


def worker_abort(worker):
    """Called when a worker receives SIGABRT (timeout)."""
    print(f"[GUNICORN] Worker {worker.pid} was killed (timeout)")


def pre_request(worker, req):
    """Called just before a request is handled."""
    pass


def post_request(worker, req, environ, resp):
    """Called after a request has been handled."""
    pass


def child_exit(server, worker):
    """Called when a worker process exits."""
    print(f"[GUNICORN] Worker {worker.pid} exited")


def worker_exit(server, worker):
    """Called when a worker process is terminated."""
    print(f"[GUNICORN] Worker {worker.pid} terminated")


def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers is changed."""
    print(f"[GUNICORN] Workers changed from {old_value} to {new_value}")
