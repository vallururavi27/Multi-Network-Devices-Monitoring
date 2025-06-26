#!/usr/bin/env python3
"""
Complete Network Monitor Application
Production-ready network monitoring solution with Flask
"""
import os
import threading
import time
import subprocess
import platform
import re
import json
import smtplib
import tempfile
from datetime import datetime, timedelta
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
import logging
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
import speedtest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('network_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///network_monitor.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = False

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

# Alert configuration
app.config['ALERT_EMAIL_RECIPIENTS'] = os.environ.get('ALERT_EMAIL_RECIPIENTS', '').split(',')
app.config['ALERT_COOLDOWN_MINUTES'] = int(os.environ.get('ALERT_COOLDOWN_MINUTES', 15))

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
mail = Mail(app)

# Define models directly in this file
class DeviceStatus(Enum):
    """Device status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    UNKNOWN = "unknown"

class Device(db.Model):
    """Device model for storing monitored devices."""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False, unique=True)
    description = db.Column(db.Text)
    device_type = db.Column(db.String(50), default='server')
    location = db.Column(db.String(100))

    # Monitoring configuration
    ping_enabled = db.Column(db.Boolean, default=True)
    ping_interval = db.Column(db.Integer, default=60)
    ping_timeout = db.Column(db.Integer, default=5)
    alert_enabled = db.Column(db.Boolean, default=True)

    # Status and metadata
    status = db.Column(db.Enum(DeviceStatus), default=DeviceStatus.UNKNOWN)
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Device {self.name} ({self.ip_address})>'

class PingResult(db.Model):
    """Ping result model for storing ping test results."""
    __tablename__ = 'ping_results'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)

    # Ping metrics
    is_reachable = db.Column(db.Boolean, nullable=False)
    response_time = db.Column(db.Float)  # milliseconds
    packet_loss = db.Column(db.Float, default=0.0)  # percentage
    error_message = db.Column(db.Text)

    # Metadata
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationship
    device = db.relationship('Device', backref='ping_results')

    def __repr__(self):
        return f'<PingResult {self.device_id} - {self.is_reachable}>'

# Simple ping monitor class
class PingMonitor:
    """Handles ping operations for network monitoring."""

    def __init__(self):
        self.system = platform.system().lower()

    def ping_host(self, host: str, timeout: int = 5, count: int = 1) -> dict:
        """
        Ping a host and return results.

        Args:
            host: IP address to ping
            timeout: Timeout in seconds
            count: Number of ping packets to send

        Returns:
            Dictionary with ping results
        """
        result = {
            'host': host,
            'is_reachable': False,
            'response_time': None,
            'packet_loss': 100.0,
            'error_message': None,
            'timestamp': time.time()
        }

        try:
            # Build ping command based on operating system
            if self.system == 'windows':
                cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), host]
            else:
                cmd = ['ping', '-c', str(count), '-W', str(timeout), host]

            # Execute ping command
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout * count + 10
            )

            if process.returncode == 0:
                # Parse successful ping output
                output = process.stdout
                parsed = self._parse_ping_output(output, self.system)
                result.update(parsed)
            else:
                # Parse error output
                error_output = process.stderr or process.stdout
                result['error_message'] = error_output.strip()

        except subprocess.TimeoutExpired:
            result['error_message'] = f"Ping command timed out"
        except Exception as e:
            result['error_message'] = f"Ping failed: {str(e)}"

        return result

    def _parse_ping_output(self, output: str, system: str) -> dict:
        """Parse ping command output to extract statistics."""
        result = {
            'is_reachable': False,
            'response_time': None,
            'packet_loss': 100.0
        }

        try:
            if system == 'windows':
                # Look for successful ping response
                if 'Reply from' in output:
                    result['is_reachable'] = True
                    result['packet_loss'] = 0.0

                    # Extract response time
                    time_match = re.search(r'time[<=](\d+)ms', output)
                    if time_match:
                        result['response_time'] = float(time_match.group(1))

                # Look for packet statistics
                packet_match = re.search(r'Lost = (\d+)', output)
                if packet_match:
                    lost = int(packet_match.group(1))
                    result['packet_loss'] = lost * 25.0  # Assuming 4 packets

            else:
                # Unix-like systems
                if '1 received' in output or '1 packets received' in output:
                    result['is_reachable'] = True
                    result['packet_loss'] = 0.0

                    # Extract response time
                    time_match = re.search(r'time=([\d.]+)', output)
                    if time_match:
                        result['response_time'] = float(time_match.group(1))

        except Exception as e:
            logger.error(f"Error parsing ping output: {str(e)}")

        return result

# Simple background monitoring without Celery
class SimpleMonitor:
    def __init__(self):
        self.ping_monitor = PingMonitor()
        self.running = False
        self.thread = None

    def start(self):
        """Start background monitoring."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.info("Background monitoring started")

    def stop(self):
        """Stop background monitoring."""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Background monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                with app.app_context():
                    self._monitor_all_devices()
                time.sleep(60)  # Monitor every minute
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(30)  # Wait 30 seconds on error

    def _monitor_all_devices(self):
        """Monitor all active devices."""
        devices = Device.query.filter_by(is_active=True).all()

        for device in devices:
            try:
                # Perform ping test
                ping_result = self.ping_monitor.ping_host(
                    device.ip_address,
                    timeout=device.ping_timeout,
                    count=1
                )

                # Store result
                db_result = PingResult(
                    device_id=device.id,
                    is_reachable=ping_result['is_reachable'],
                    response_time=ping_result['response_time'],
                    packet_loss=ping_result['packet_loss'],
                    error_message=ping_result.get('error_message')
                )

                db.session.add(db_result)

                # Update device status
                if ping_result['is_reachable']:
                    device.status = DeviceStatus.ONLINE
                    device.last_seen = datetime.utcnow()
                else:
                    device.status = DeviceStatus.OFFLINE

                db.session.commit()
                logger.info(f"Monitored {device.name}: {device.status.value}")

            except Exception as e:
                logger.error(f"Error monitoring {device.name}: {e}")
                db.session.rollback()

# Initialize monitor
monitor = SimpleMonitor()

# Routes
@app.route('/')
def dashboard():
    """Dashboard page."""
    # Get device status summary
    devices = Device.query.filter_by(is_active=True).all()
    
    status_summary = {
        'total': len(devices),
        'online': len([d for d in devices if d.status == DeviceStatus.ONLINE]),
        'offline': len([d for d in devices if d.status == DeviceStatus.OFFLINE]),
        'warning': len([d for d in devices if d.status == DeviceStatus.WARNING]),
        'unknown': len([d for d in devices if d.status == DeviceStatus.UNKNOWN])
    }
    
    # Get recent ping results
    recent_pings = PingResult.query.join(Device)\
        .order_by(PingResult.timestamp.desc())\
        .limit(20).all()
    
    return render_template('dashboard_simple.html',
                         status_summary=status_summary,
                         recent_pings=recent_pings,
                         devices=devices)

@app.route('/devices')
def devices():
    """Device list page."""
    devices = Device.query.all()
    return render_template('devices_simple.html', devices=devices)

@app.route('/add_device', methods=['GET', 'POST'])
def add_device():
    """Add device page."""
    if request.method == 'POST':
        try:
            device = Device(
                name=request.form['name'],
                ip_address=request.form['ip_address'],
                description=request.form.get('description', ''),
                device_type=request.form.get('device_type', 'server'),
                location=request.form.get('location', ''),
                ping_enabled=True,
                alert_enabled=True,
                status=DeviceStatus.UNKNOWN
            )
            
            db.session.add(device)
            db.session.commit()
            
            flash(f'Device {device.name} added successfully!', 'success')
            return redirect(url_for('devices'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding device: {str(e)}', 'error')
    
    return render_template('add_device_simple.html')

@app.route('/test_device/<int:device_id>')
def test_device(device_id):
    """Test device connectivity."""
    device = Device.query.get_or_404(device_id)
    
    try:
        ping_result = monitor.ping_monitor.ping_host(device.ip_address, timeout=5, count=1)
        
        return jsonify({
            'success': True,
            'device_name': device.name,
            'is_reachable': ping_result['is_reachable'],
            'response_time': ping_result['response_time'],
            'error_message': ping_result.get('error_message')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/status')
def api_status():
    """API status endpoint."""
    devices = Device.query.filter_by(is_active=True).all()
    
    status_summary = {
        'total': len(devices),
        'online': len([d for d in devices if d.status == DeviceStatus.ONLINE]),
        'offline': len([d for d in devices if d.status == DeviceStatus.OFFLINE]),
        'warning': len([d for d in devices if d.status == DeviceStatus.WARNING]),
        'unknown': len([d for d in devices if d.status == DeviceStatus.UNKNOWN])
    }
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'device_summary': status_summary
    })

@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        device_count = Device.query.count()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'devices': device_count,
            'monitoring': 'active' if monitor.running else 'inactive'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Initialize database
def init_db():
    """Initialize database with sample data."""
    with app.app_context():
        db.create_all()
        
        # Add sample devices if none exist
        if Device.query.count() == 0:
            sample_devices = [
                Device(
                    name='Google DNS',
                    ip_address='8.8.8.8',
                    description='Google Public DNS Server',
                    device_type='dns_server',
                    location='Internet',
                    status=DeviceStatus.UNKNOWN
                ),
                Device(
                    name='Cloudflare DNS',
                    ip_address='1.1.1.1',
                    description='Cloudflare Public DNS Server',
                    device_type='dns_server',
                    location='Internet',
                    status=DeviceStatus.UNKNOWN
                ),
                Device(
                    name='Local Gateway',
                    ip_address='192.168.1.1',
                    description='Default local network gateway',
                    device_type='router',
                    location='Local Network',
                    status=DeviceStatus.UNKNOWN
                )
            ]
            
            for device in sample_devices:
                db.session.add(device)
            
            db.session.commit()
            logger.info("Sample devices added to database")

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Start background monitoring
    monitor.start()
    
    try:
        # Run Flask app
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        # Stop monitoring on exit
        monitor.stop()
