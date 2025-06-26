# 🌐 Multi-Network Devices Monitoring System

A comprehensive, enterprise-grade network monitoring solution built with Django that supports monitoring 1000+ devices with real-time status tracking, advanced filtering, and comprehensive service monitoring.

![Network Monitor Dashboard](https://img.shields.io/badge/Django-5.2.3-green) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Open Source](https://img.shields.io/badge/Open%20Source-❤️-red)

## 💝 Support This Project

This project is **completely free and open source**. If you find it useful, please consider supporting its development:

[![GitHub Stars](https://img.shields.io/github/stars/vallururavi27/Multi-Network-Devices-Monitoring?style=social)](https://github.com/vallururavi27/Multi-Network-Devices-Monitoring)
[![PayPal Donate](https://img.shields.io/badge/PayPal-Donate-blue?logo=paypal)](https://paypal.me/vallururavi27)

- ⭐ **Star this repository** on GitHub
- 💰 **[Donate via PayPal](https://paypal.me/vallururavi27)** to support development
- 🐛 **Report bugs** and suggest features
- 🤝 **Contribute** code improvements
- 📢 **Share** with others who might find it useful

Your support helps maintain and improve this tool for everyone! 🙏

## ✨ Features

- 🔍 **Real-time Monitoring** - Monitor multiple IP addresses simultaneously
- ⚡ **Speed Testing** - Built-in network speed testing capabilities
- 📧 **Email Alerts** - Automated notifications for device status changes
- 📊 **Excel Integration** - Import IP lists and export monitoring results
- ⏰ **Scheduled Tasks** - Automated monitoring with configurable intervals
- 📈 **Historical Data** - Track performance trends over time
- 🎨 **Modern UI** - Clean, responsive web interface
- 🔒 **Secure** - Input validation and secure configuration management

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Redis server (for background tasks)
- SMTP server access (for email alerts)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd network-monitor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Start Redis server**
   ```bash
   redis-server
   ```

7. **Start Celery worker** (in a new terminal)
   ```bash
   celery -A app.celery worker --loglevel=info
   ```

8. **Start Celery beat scheduler** (in a new terminal)
   ```bash
   celery -A app.celery beat --loglevel=info
   ```

9. **Run the application**
   ```bash
   python app.py
   ```

Visit `http://localhost:5000` to access the web interface.

## 📖 Documentation

### Configuration

All configuration is done through environment variables. Copy `.env.example` to `.env` and modify the values:

- **Database**: Configure your database URL
- **Redis**: Set Redis connection details for background tasks
- **Email**: Configure SMTP settings for alerts
- **Monitoring**: Set default timeouts and intervals
- **Security**: Configure CSRF protection and secret keys

### API Endpoints

The application provides RESTful API endpoints for programmatic access:

- `GET /api/devices` - List all monitored devices
- `POST /api/devices` - Add a new device
- `GET /api/devices/{id}/status` - Get device status
- `GET /api/monitoring/results` - Get monitoring results
- `POST /api/alerts/test` - Test alert configuration

### Excel Integration

- **Import**: Upload Excel files with IP addresses and device information
- **Export**: Download monitoring results and reports in Excel format

## 🏗️ Architecture

- **Flask**: Web framework and API
- **SQLAlchemy**: Database ORM
- **Celery**: Background task processing
- **Redis**: Message broker and caching
- **Bootstrap**: Responsive UI framework

## 🧪 Testing

Run the test suite:

```bash
pytest
pytest --cov=app  # With coverage report
```

## 🚀 Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Using Docker

```bash
docker build -t network-monitor .
docker run -p 8000:8000 network-monitor
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions, please open an issue on GitHub.
