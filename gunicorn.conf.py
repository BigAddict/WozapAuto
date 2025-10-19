# Gunicorn configuration for WozapAuto
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:58741"
backlog = 2048

# Worker processes
workers = 3
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased from default 30 seconds to 120 seconds
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'wozapauto'

# Server mechanics
daemon = False
pidfile = '/tmp/wozapauto.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Worker timeout and memory management
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance
preload_app = True

# Graceful timeout for worker shutdown
graceful_timeout = 30

# Environment variables
raw_env = [
    'DJANGO_SETTINGS_MODULE=base.settings',
]

def when_ready(server):
    server.log.info("WozapAuto server is ready. Workers: %s", server.cfg.workers)

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")
