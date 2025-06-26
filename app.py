#!/usr/bin/env python3
"""
Network Monitor Application Entry Point
"""
import os
from app import create_app, make_celery

# Create Flask application
app = create_app()

# Create Celery instance
celery = make_celery(app)

# Import Celery tasks to register them
from app.tasks import *

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config.get('DEBUG', False)
    )
