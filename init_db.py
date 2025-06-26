#!/usr/bin/env python3
"""
Database initialization script for Network Monitor
"""
import os
from app import create_app, db
from app.models import Device, SystemSettings, DeviceStatus
from flask_migrate import init, migrate, upgrade

def init_database():
    """Initialize the database with tables and default data."""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Add default system settings
        default_settings = [
            {
                'key': 'app_name',
                'value': 'Network Monitor',
                'description': 'Application name displayed in UI',
                'data_type': 'string'
            },
            {
                'key': 'default_ping_timeout',
                'value': '5',
                'description': 'Default ping timeout in seconds',
                'data_type': 'integer'
            },
            {
                'key': 'default_ping_interval',
                'value': '60',
                'description': 'Default ping interval in seconds',
                'data_type': 'integer'
            },
            {
                'key': 'max_ping_history_days',
                'value': '30',
                'description': 'Maximum days to keep ping history',
                'data_type': 'integer'
            },
            {
                'key': 'alert_cooldown_minutes',
                'value': '15',
                'description': 'Minimum minutes between duplicate alerts',
                'data_type': 'integer'
            },
            {
                'key': 'enable_speed_tests',
                'value': 'true',
                'description': 'Enable speed testing functionality',
                'data_type': 'boolean'
            },
            {
                'key': 'speed_test_servers',
                'value': '[]',
                'description': 'Preferred speed test servers (JSON array)',
                'data_type': 'json'
            },
            {
                'key': 'dashboard_refresh_interval',
                'value': '30',
                'description': 'Dashboard auto-refresh interval in seconds',
                'data_type': 'integer'
            },
            {
                'key': 'max_concurrent_pings',
                'value': '50',
                'description': 'Maximum concurrent ping operations',
                'data_type': 'integer'
            },
            {
                'key': 'email_notifications_enabled',
                'value': 'true',
                'description': 'Enable email notifications for alerts',
                'data_type': 'boolean'
            }
        ]
        
        for setting_data in default_settings:
            existing = SystemSettings.query.filter_by(key=setting_data['key']).first()
            if not existing:
                setting = SystemSettings(**setting_data)
                db.session.add(setting)
        
        # Add sample devices for demonstration
        sample_devices = [
            {
                'name': 'Google DNS',
                'ip_address': '8.8.8.8',
                'description': 'Google Public DNS Server',
                'device_type': 'dns_server',
                'location': 'Internet',
                'ping_enabled': True,
                'alert_enabled': True,
                'status': DeviceStatus.UNKNOWN
            },
            {
                'name': 'Cloudflare DNS',
                'ip_address': '1.1.1.1',
                'description': 'Cloudflare Public DNS Server',
                'device_type': 'dns_server',
                'location': 'Internet',
                'ping_enabled': True,
                'alert_enabled': True,
                'status': DeviceStatus.UNKNOWN
            },
            {
                'name': 'Local Gateway',
                'ip_address': '192.168.1.1',
                'description': 'Default local network gateway',
                'device_type': 'router',
                'location': 'Local Network',
                'ping_enabled': True,
                'alert_enabled': True,
                'status': DeviceStatus.UNKNOWN
            }
        ]
        
        for device_data in sample_devices:
            existing = Device.query.filter_by(ip_address=device_data['ip_address']).first()
            if not existing:
                device = Device(**device_data)
                db.session.add(device)
        
        # Commit all changes
        db.session.commit()
        print("Database initialized successfully!")
        print(f"Added {len(default_settings)} system settings")
        print(f"Added {len(sample_devices)} sample devices")

def setup_migrations():
    """Set up Flask-Migrate for database migrations."""
    app = create_app()
    
    with app.app_context():
        if not os.path.exists('migrations'):
            print("Initializing migrations...")
            init()
            print("Creating initial migration...")
            migrate(message='Initial migration')
            print("Applying migration...")
            upgrade()
        else:
            print("Migrations directory already exists")
            print("Applying any pending migrations...")
            upgrade()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        setup_migrations()
    else:
        init_database()
