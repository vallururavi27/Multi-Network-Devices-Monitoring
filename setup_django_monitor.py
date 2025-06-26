#!/usr/bin/env python3
"""
Django Network Monitor Setup Script
Complete setup for production-ready network monitoring with Django
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def create_env_file():
    """Create .env file with default settings"""
    env_content = """# Django Settings
SECRET_KEY=django-network-monitor-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database (SQLite by default)
DATABASE_URL=sqlite:///db.sqlite3

# Redis (for Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@networkmonitor.com

# Network Monitor Settings
DEFAULT_PING_TIMEOUT=5
DEFAULT_PING_INTERVAL=60
MAX_CONCURRENT_PINGS=50
SPEED_TEST_INTERVAL=3600
ALERT_COOLDOWN_MINUTES=15
ALERT_EMAIL_RECIPIENTS=admin@example.com,ops@example.com
MAX_PING_HISTORY_DAYS=30
DASHBOARD_REFRESH_INTERVAL=30
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    print("✅ Created .env file with default settings")

def create_directories():
    """Create necessary directories"""
    directories = [
        'static/css',
        'static/js',
        'static/img',
        'templates/base',
        'templates/devices',
        'templates/monitoring',
        'templates/alerts',
        'templates/reports',
        'media/uploads',
        'logs',
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created directory structure")

def create_base_template():
    """Create base Django template"""
    template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Network Monitor{% endblock %}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    {% load static %}
    <link rel="stylesheet" href="{% static 'css/custom.css' %}">
    
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="{% url 'monitoring:dashboard' %}">
                <i class="bi bi-router"></i> Network Monitor
            </a>
            
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'monitoring:dashboard' %}">
                            <i class="bi bi-speedometer2"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'devices:list' %}">
                            <i class="bi bi-hdd-network"></i> Devices
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'monitoring:live' %}">
                            <i class="bi bi-activity"></i> Live Monitor
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'alerts:list' %}">
                            <i class="bi bi-exclamation-triangle"></i> Alerts
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'reports:index' %}">
                            <i class="bi bi-graph-up"></i> Reports
                        </a>
                    </li>
                </ul>
                
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/admin/">
                            <i class="bi bi-gear"></i> Admin
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container-fluid">
        <!-- Messages -->
        {% if messages %}
            <div class="mt-3">
                {% for message in messages %}
                    <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
        
        <!-- Page Content -->
        <div class="mt-3">
            {% block content %}{% endblock %}
        </div>
    </div>

    <!-- Footer -->
    <footer class="bg-light text-center text-muted py-3 mt-5">
        <div class="container">
            <small>&copy; 2024 Network Monitor. Built with Django and Bootstrap.</small>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>"""
    
    with open('templates/base.html', 'w') as f:
        f.write(template_content)
    print("✅ Created base template")

def create_custom_css():
    """Create custom CSS file"""
    css_content = """.status-online { color: #28a745; }
.status-offline { color: #dc3545; }
.status-warning { color: #ffc107; }
.status-unknown { color: #6c757d; }

.card-metric { text-align: center; }
.card-metric .metric-value { font-size: 2rem; font-weight: bold; }
.card-metric .metric-label { color: #6c757d; }

.device-status-badge {
    font-size: 0.875rem;
    padding: 0.375rem 0.75rem;
}

.ping-result-success { background-color: #d4edda; }
.ping-result-failed { background-color: #f8d7da; }

.navbar-brand { font-weight: bold; }

.table-hover tbody tr:hover {
    background-color: rgba(0, 0, 0, 0.075);
}

.chart-container {
    position: relative;
    height: 400px;
    width: 100%;
}

.alert-item {
    border-left: 4px solid;
}

.alert-item.severity-high { border-left-color: #dc3545; }
.alert-item.severity-medium { border-left-color: #ffc107; }
.alert-item.severity-low { border-left-color: #17a2b8; }

.device-card {
    transition: transform 0.2s;
}

.device-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.monitoring-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
}

@media (max-width: 768px) {
    .monitoring-grid {
        grid-template-columns: 1fr;
    }
}"""
    
    with open('static/css/custom.css', 'w') as f:
        f.write(css_content)
    print("✅ Created custom CSS")

def main():
    """Main setup function"""
    print("🚀 Django Network Monitor Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path('manage.py').exists():
        print("❌ manage.py not found. Please run this script from the Django project root.")
        sys.exit(1)
    
    # Create environment file
    if not Path('.env').exists():
        create_env_file()
    else:
        print("ℹ️  .env file already exists")
    
    # Create directories
    create_directories()
    
    # Create templates and static files
    create_base_template()
    create_custom_css()
    
    # Install dependencies
    print("\n📦 Installing Dependencies...")
    if not run_command("pip install -r requirements_django.txt", "Installing Python packages"):
        print("⚠️  Some packages failed to install. You may need to install them manually.")
    
    # Django setup
    print("\n🔧 Setting up Django...")
    
    # Make migrations
    run_command("python manage.py makemigrations", "Creating migrations")
    run_command("python manage.py migrate", "Applying migrations")
    
    # Create superuser (optional)
    print("\n👤 Creating superuser...")
    print("You can create a superuser account to access the Django admin.")
    create_superuser = input("Create superuser now? (y/n): ").lower().strip()
    
    if create_superuser == 'y':
        run_command("python manage.py createsuperuser", "Creating superuser")
    
    # Collect static files
    run_command("python manage.py collectstatic --noinput", "Collecting static files")
    
    print("\n✅ Setup completed successfully!")
    print("\n🎉 Your Django Network Monitor is ready!")
    print("\nNext steps:")
    print("1. Start Redis server: redis-server")
    print("2. Start Celery worker: celery -A network_monitor worker --loglevel=info")
    print("3. Start Celery beat: celery -A network_monitor beat --loglevel=info")
    print("4. Start Django server: python manage.py runserver")
    print("5. Open http://127.0.0.1:8000 in your browser")
    print("\nAdmin panel: http://127.0.0.1:8000/admin/")
    print("\nFor production deployment, see the documentation.")

if __name__ == '__main__':
    main()
