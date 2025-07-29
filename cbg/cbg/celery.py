from __future__ import absolute_import, unicode_literals
import os
import platform
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbg.settings')

app = Celery('cbg')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Windows-specific configuration
if platform.system().lower() == 'windows':
    # Use threads pool on Windows since it doesn't support fork()
    app.conf.update(
        task_always_eager=False,
        worker_pool_restarts=True,
        worker_pool='threads',
        worker_concurrency=1,
    )
