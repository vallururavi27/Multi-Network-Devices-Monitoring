# Django Network Monitor

A complete, production-ready network monitoring solution built with Django.

## 🚀 Features

- **Real-time Network Monitoring** - Monitor multiple IP addresses with ping tests
- **Speed Testing** - Built-in network speed testing capabilities
- **Email Alerts** - Automated notifications for device status changes
- **Excel Integration** - Import device lists and export monitoring results
- **Modern Web UI** - Clean, responsive interface built with Bootstrap 5
- **REST API** - Full API for integration with other systems
- **Background Tasks** - Celery-powered background monitoring
- **Historical Data** - Track performance trends over time
- **Device Management** - Organize devices into groups
- **Alert Management** - Comprehensive alerting system
- **System Health** - Monitor the monitoring system itself

## 📋 Requirements

- Python 3.8+
- Redis (for Celery)
- Django 4.2+
- Modern web browser

## 🛠️ Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements_django.txt
```

### 2. Run Setup Script

```bash
python setup_django_monitor.py
```

This will:
- Create necessary directories
- Set up environment configuration
- Create database tables
- Set up static files
- Create a superuser (optional)

### 3. Start Services

**Terminal 1 - Redis:**
```bash
redis-server
```

**Terminal 2 - Celery Worker:**
```bash
celery -A network_monitor worker --loglevel=info
```

**Terminal 3 - Celery Beat (Scheduler):**
```bash
celery -A network_monitor beat --loglevel=info
```

**Terminal 4 - Django Server:**
```bash
python manage.py runserver
```

### 4. Access the Application

- **Web Interface**: http://127.0.0.1:8000
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **API Documentation**: http://127.0.0.1:8000/api/

## 📱 Application Structure

```
network_monitor/
├── network_monitor/          # Django project settings
├── devices/                  # Device management app
├── monitoring/              # Core monitoring functionality
├── alerts/                  # Alert system
├── reports/                 # Reporting and exports
├── templates/               # HTML templates
├── static/                  # CSS, JS, images
└── media/                   # Uploaded files
```

## 🎯 Key Components

### Device Management
- Add/edit/delete devices
- Bulk operations
- Device grouping
- Excel import/export
- Device credentials management

### Monitoring Engine
- Automated ping tests every 5 minutes
- Speed tests on configurable intervals
- Real-time status updates
- Historical data retention
- Performance metrics

### Alert System
- Email notifications
- Configurable alert rules
- Alert acknowledgment
- Cooldown periods
- Multiple notification channels

### Web Interface
- Dashboard with real-time updates
- Live monitoring view
- Device detail pages
- Alert management
- System health monitoring

## 🔧 Configuration

### Environment Variables (.env)

```env
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Monitoring
DEFAULT_PING_TIMEOUT=5
DEFAULT_PING_INTERVAL=60
ALERT_EMAIL_RECIPIENTS=admin@example.com
```

### Network Monitor Settings

```python
NETWORK_MONITOR = {
    'DEFAULT_PING_TIMEOUT': 5,
    'DEFAULT_PING_INTERVAL': 60,
    'MAX_CONCURRENT_PINGS': 50,
    'SPEED_TEST_INTERVAL': 3600,
    'ALERT_COOLDOWN_MINUTES': 15,
    'MAX_PING_HISTORY_DAYS': 30,
}
```

## 📊 API Endpoints

### Devices
- `GET /api/devices/` - List all devices
- `POST /api/devices/` - Create device
- `GET /api/devices/{id}/` - Get device details
- `PUT /api/devices/{id}/` - Update device
- `DELETE /api/devices/{id}/` - Delete device

### Monitoring
- `GET /api/monitoring/dashboard/` - Dashboard data
- `GET /api/monitoring/device/{id}/` - Device status
- `POST /api/monitoring/test/{id}/` - Test device
- `GET /api/monitoring/results/` - Monitoring results

### Alerts
- `GET /api/alerts/` - List alerts
- `POST /api/alerts/{id}/acknowledge/` - Acknowledge alert
- `GET /api/alerts/rules/` - Alert rules

## 🔄 Background Tasks

### Celery Tasks
- `monitor_all_devices` - Monitor all active devices (every 5 minutes)
- `send_pending_alerts` - Send email alerts (every 2 minutes)
- `cleanup_old_data` - Clean up old data (daily)
- `update_system_metrics` - Update system metrics (hourly)

### Task Monitoring
```bash
# View active tasks
celery -A network_monitor inspect active

# View task history
celery -A network_monitor events

# Monitor task queue
celery -A network_monitor flower
```

## 📈 Monitoring Features

### Dashboard
- Device status overview
- Real-time charts
- Recent alerts
- System metrics
- Quick actions

### Live Monitor
- Real-time device status
- Auto-refresh every 30 seconds
- Response time graphs
- Uptime statistics

### Device Details
- Historical ping results
- Speed test results
- Performance charts
- Alert history

## 🚨 Alert System

### Alert Types
- Device Down/Up
- High Latency
- Packet Loss
- Speed Degradation

### Notification Channels
- Email notifications
- Slack integration (configurable)
- Webhook notifications
- SMS alerts (configurable)

## 📋 Excel Integration

### Import Devices
Upload Excel files with device information:
- Required columns: name, ip_address
- Optional columns: description, device_type, location

### Export Data
- Device lists
- Monitoring results
- Performance reports
- Alert summaries

## 🔒 Security

### Production Settings
- Change SECRET_KEY
- Set DEBUG=False
- Configure ALLOWED_HOSTS
- Use HTTPS
- Secure database credentials

### Authentication
- Django admin authentication
- Session-based authentication
- CSRF protection
- XSS protection

## 🐳 Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
  
  worker:
    build: .
    command: celery -A network_monitor worker
    depends_on:
      - redis
  
  beat:
    build: .
    command: celery -A network_monitor beat
    depends_on:
      - redis
```

## 🔧 Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Start Redis
   redis-server
   
   # Check Redis status
   redis-cli ping
   ```

2. **Celery Tasks Not Running**
   ```bash
   # Check worker status
   celery -A network_monitor inspect stats
   
   # Restart worker
   celery -A network_monitor worker --loglevel=info
   ```

3. **Database Errors**
   ```bash
   # Reset database
   python manage.py migrate --run-syncdb
   
   # Create superuser
   python manage.py createsuperuser
   ```

4. **Permission Errors**
   ```bash
   # Fix file permissions
   chmod +x manage.py
   chmod +x setup_django_monitor.py
   ```

## 📚 Development

### Adding New Features
1. Create new Django apps for major features
2. Add models in `models.py`
3. Create views in `views.py`
4. Add URL patterns in `urls.py`
5. Create templates in `templates/`
6. Add Celery tasks in `tasks.py`

### Testing
```bash
# Run tests
python manage.py test

# Run specific app tests
python manage.py test devices

# Coverage report
coverage run --source='.' manage.py test
coverage report
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Review Django and Celery documentation
- Open an issue on GitHub

---

**Built with ❤️ using Django, Celery, and Bootstrap**
