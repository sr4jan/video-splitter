# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "0.0.0.0:10000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 300  # Increased timeout to 5 minutes
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'gunicorn_modern_video_splitter'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Larger buffer size for file uploads
worker_tmp_dir = '/tmp'
max_requests = 1000
max_requests_jitter = 50

# Increase timeouts
graceful_timeout = 300
keep_alive = 5