#!/usr/bin/env python3
"""
Network Monitor Startup Script
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def check_requirements():
    """Check if all requirements are installed."""
    try:
        import flask
        import celery
        import redis
        import ping3
        import speedtest
        import openpyxl
        import pandas
        print("✓ All required packages are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_redis():
    """Check if Redis is running."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✓ Redis is running")
        return True
    except Exception:
        print("✗ Redis is not running")
        print("Please start Redis server: redis-server")
        return False

def setup_environment():
    """Setup environment variables."""
    env_file = Path('.env')
    if not env_file.exists():
        print("Creating .env file from template...")
        example_file = Path('.env.example')
        if example_file.exists():
            import shutil
            shutil.copy('.env.example', '.env')
            print("✓ Created .env file")
            print("Please edit .env file with your configuration")
        else:
            print("✗ .env.example file not found")
            return False
    else:
        print("✓ .env file exists")
    return True

def initialize_database():
    """Initialize the database."""
    try:
        print("Initializing database...")
        result = subprocess.run([sys.executable, 'init_db.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Database initialized successfully")
            return True
        else:
            print(f"✗ Database initialization failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        return False

def start_celery_worker():
    """Start Celery worker in background."""
    try:
        print("Starting Celery worker...")
        subprocess.Popen([
            sys.executable, '-m', 'celery', 
            '-A', 'app.celery', 'worker', 
            '--loglevel=info'
        ])
        print("✓ Celery worker started")
        return True
    except Exception as e:
        print(f"✗ Error starting Celery worker: {e}")
        return False

def start_celery_beat():
    """Start Celery beat scheduler in background."""
    try:
        print("Starting Celery beat scheduler...")
        subprocess.Popen([
            sys.executable, '-m', 'celery', 
            '-A', 'app.celery', 'beat', 
            '--loglevel=info'
        ])
        print("✓ Celery beat scheduler started")
        return True
    except Exception as e:
        print(f"✗ Error starting Celery beat: {e}")
        return False

def start_flask_app():
    """Start Flask application."""
    try:
        print("Starting Flask application...")
        print("Access the application at: http://localhost:5000")
        print("Press Ctrl+C to stop")
        
        os.environ['FLASK_APP'] = 'app.py'
        os.environ['FLASK_ENV'] = 'development'
        
        subprocess.run([sys.executable, 'app.py'])
        return True
    except KeyboardInterrupt:
        print("\nShutting down...")
        return True
    except Exception as e:
        print(f"✗ Error starting Flask app: {e}")
        return False

def main():
    """Main startup function."""
    print("🚀 Network Monitor Startup")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Check Redis
    if not check_redis():
        print("Please start Redis and try again")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        sys.exit(1)
    
    # Start background services
    start_celery_worker()
    time.sleep(2)  # Give worker time to start
    
    start_celery_beat()
    time.sleep(2)  # Give beat time to start
    
    # Start Flask app
    start_flask_app()

if __name__ == '__main__':
    main()
