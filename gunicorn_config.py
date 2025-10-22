# Gunicorn Configuration File
# Place this file in your project root

import multiprocessing
import os

# Server socket
bind = "unix:/tmp/gunicorn.sock"
backlog = 2048

# Worker processes
# For 1GB RAM: 2 workers
# For 2GB RAM: 3-4 workers  
# For 4GB RAM: 5-8 workers
workers = int(os.getenv('GUNICORN_WORKERS', '2'))
worker_class = 'sync'
worker_connections = 100
threads = int(os.getenv('GUNICORN_THREADS', '2'))
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30
keepalive = 5

# Process naming
proc_name = 'computershop'

# Logging
accesslog = '/var/log/gunicorn/access.log'
errorlog = '/var/log/gunicorn/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process management
daemon = False
pidfile = '/tmp/gunicorn.pid'
umask = 0
user = None
group = None
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
preload_app = True
sendfile = True
reuse_port = False
chdir = os.getcwd()

# SSL (if needed)
keyfile = None
certfile = None

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    pass

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")

