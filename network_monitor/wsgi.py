"""
WSGI config for network_monitor project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')

application = get_wsgi_application()
