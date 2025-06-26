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
import ipaddress
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
from openpyxl.utils.dataframe import dataframe_to_rows

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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'network-monitor-secret-key-2024')
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
app.config['ALERT_EMAIL_RECIPIENTS'] = [r.strip() for r in os.environ.get('ALERT_EMAIL_RECIPIENTS', '').split(',') if r.strip()]
app.config['ALERT_COOLDOWN_MINUTES'] = int(os.environ.get('ALERT_COOLDOWN_MINUTES', 15))

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
mail = Mail(app)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class DeviceStatus(Enum):
    """Device status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    UNKNOWN = "unknown"

class AlertType(Enum):
    """Alert type enumeration."""
    DEVICE_DOWN = "device_down"
    DEVICE_UP = "device_up"
    HIGH_LATENCY = "high_latency"
    SPEED_DEGRADATION = "speed_degradation"
    TIMEOUT = "timeout"

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
    speed_test_enabled = db.Column(db.Boolean, default=False)
    speed_test_interval = db.Column(db.Integer, default=3600)
    
    # Alert configuration
    alert_enabled = db.Column(db.Boolean, default=True)
    alert_threshold_latency = db.Column(db.Float, default=1000.0)
    alert_threshold_packet_loss = db.Column(db.Float, default=10.0)
    
    # Status and metadata
    status = db.Column(db.Enum(DeviceStatus), default=DeviceStatus.UNKNOWN)
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Device {self.name} ({self.ip_address})>'
    
    def to_dict(self):
        """Convert device to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'description': self.description,
            'device_type': self.device_type,
            'location': self.location,
            'status': self.status.value if self.status else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'ping_enabled': self.ping_enabled,
            'speed_test_enabled': self.speed_test_enabled,
            'alert_enabled': self.alert_enabled,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

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
    
    def to_dict(self):
        """Convert ping result to dictionary."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'is_reachable': self.is_reachable,
            'response_time': self.response_time,
            'packet_loss': self.packet_loss,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat()
        }

class SpeedTestResult(db.Model):
    """Speed test result model for storing network speed test results."""
    __tablename__ = 'speed_test_results'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    
    # Speed test metrics
    download_speed = db.Column(db.Float)  # Mbps
    upload_speed = db.Column(db.Float)  # Mbps
    ping_latency = db.Column(db.Float)  # milliseconds
    server_name = db.Column(db.String(100))
    server_location = db.Column(db.String(100))
    
    # Test metadata
    test_duration = db.Column(db.Float)  # seconds
    error_message = db.Column(db.Text)
    is_successful = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    device = db.relationship('Device', backref='speed_results')
    
    def __repr__(self):
        return f'<SpeedTestResult {self.device_id} - {self.download_speed}Mbps>'
    
    def to_dict(self):
        """Convert speed test result to dictionary."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'download_speed': self.download_speed,
            'upload_speed': self.upload_speed,
            'ping_latency': self.ping_latency,
            'server_name': self.server_name,
            'server_location': self.server_location,
            'test_duration': self.test_duration,
            'error_message': self.error_message,
            'is_successful': self.is_successful,
            'timestamp': self.timestamp.isoformat()
        }

class Alert(db.Model):
    """Alert model for storing alert notifications."""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    
    # Alert details
    alert_type = db.Column(db.Enum(AlertType), nullable=False)
    severity = db.Column(db.String(20), default='medium')
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Alert status
    is_active = db.Column(db.Boolean, default=True)
    is_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.String(100))
    acknowledged_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Notification tracking
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    retry_count = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    device = db.relationship('Device', backref='alerts')
    
    def __repr__(self):
        return f'<Alert {self.alert_type.value} - {self.device_id}>'
    
    def to_dict(self):
        """Convert alert to dictionary."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'alert_type': self.alert_type.value,
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'is_active': self.is_active,
            'is_acknowledged': self.is_acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'email_sent': self.email_sent,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class SystemSettings(db.Model):
    """System settings model for application configuration."""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')
    is_sensitive = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemSettings {self.key}>'
    
    def get_value(self):
        """Get typed value based on data_type."""
        if self.data_type == 'integer':
            return int(self.value) if self.value else 0
        elif self.data_type == 'float':
            return float(self.value) if self.value else 0.0
        elif self.data_type == 'boolean':
            return self.value.lower() == 'true' if self.value else False
        elif self.data_type == 'json':
            return json.loads(self.value) if self.value else {}
        else:
            return self.value or ''

# ============================================================================
# MONITORING ENGINE
# ============================================================================

class PingMonitor:
    """Handles ping operations for network monitoring."""

    def __init__(self):
        self.system = platform.system().lower()

    def ping_host(self, host: str, timeout: int = 5, count: int = 4) -> dict:
        """
        Ping a host and return detailed results.

        Args:
            host: IP address or hostname to ping
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
            'packets_sent': count,
            'packets_received': 0,
            'min_time': None,
            'max_time': None,
            'avg_time': None,
            'error_message': None,
            'timestamp': time.time()
        }

        try:
            # Validate IP address
            try:
                ipaddress.ip_address(host)
            except ValueError:
                result['error_message'] = f"Invalid IP address: {host}"
                return result

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
            result['error_message'] = f"Ping command timed out after {timeout * count + 10} seconds"
        except Exception as e:
            result['error_message'] = f"Ping failed: {str(e)}"

        return result

    def _parse_ping_output(self, output: str, system: str) -> dict:
        """Parse ping command output to extract statistics."""
        result = {
            'is_reachable': False,
            'response_time': None,
            'packet_loss': 100.0,
            'packets_sent': 0,
            'packets_received': 0,
            'min_time': None,
            'max_time': None,
            'avg_time': None
        }

        try:
            if system == 'windows':
                # Parse Windows ping output
                packet_match = re.search(r'Packets: Sent = (\d+), Received = (\d+), Lost = (\d+)', output)
                if packet_match:
                    sent, received, lost = map(int, packet_match.groups())
                    result['packets_sent'] = sent
                    result['packets_received'] = received
                    result['packet_loss'] = (lost / sent) * 100 if sent > 0 else 100.0
                    result['is_reachable'] = received > 0

                # Look for timing statistics
                time_match = re.search(r'Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms', output)
                if time_match:
                    min_time, max_time, avg_time = map(int, time_match.groups())
                    result['min_time'] = min_time
                    result['max_time'] = max_time
                    result['avg_time'] = avg_time
                    result['response_time'] = avg_time

            else:
                # Parse Unix-like ping output
                packet_match = re.search(r'(\d+) packets transmitted, (\d+) (?:packets )?received', output)
                if packet_match:
                    sent, received = map(int, packet_match.groups())
                    result['packets_sent'] = sent
                    result['packets_received'] = received
                    result['packet_loss'] = ((sent - received) / sent) * 100 if sent > 0 else 100.0
                    result['is_reachable'] = received > 0

                # Look for timing statistics
                time_match = re.search(r'min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms', output)
                if time_match:
                    min_time, avg_time, max_time, mdev = map(float, time_match.groups())
                    result['min_time'] = min_time
                    result['max_time'] = max_time
                    result['avg_time'] = avg_time
                    result['response_time'] = avg_time

        except Exception as e:
            logger.error(f"Error parsing ping output: {str(e)}")

        return result

class SpeedTestMonitor:
    """Handles network speed testing operations."""

    def __init__(self):
        self.lock = threading.Lock()

    def run_speed_test(self, timeout: int = 120) -> dict:
        """
        Run a comprehensive speed test.

        Args:
            timeout: Maximum time to wait for test completion

        Returns:
            Dictionary with speed test results
        """
        result = {
            'download_speed': None,
            'upload_speed': None,
            'ping_latency': None,
            'server_name': None,
            'server_location': None,
            'server_country': None,
            'server_sponsor': None,
            'server_id': None,
            'test_duration': None,
            'is_successful': False,
            'error_message': None,
            'timestamp': time.time(),
            'client_ip': None,
            'client_isp': None
        }

        start_time = time.time()

        try:
            with self.lock:
                st = speedtest.Speedtest()

                # Get client configuration
                config = st.get_config()
                result['client_ip'] = config.get('client', {}).get('ip')
                result['client_isp'] = config.get('client', {}).get('isp')

                # Get best server
                st.get_best_server()
                server_info = st.results.server

                result['server_name'] = server_info.get('name')
                result['server_location'] = f"{server_info.get('name')}, {server_info.get('country')}"
                result['server_country'] = server_info.get('country')
                result['server_sponsor'] = server_info.get('sponsor')
                result['server_id'] = server_info.get('id')

                # Perform ping test
                result['ping_latency'] = round(st.results.ping, 2)

                # Perform download test
                download_speed = st.download()
                result['download_speed'] = round(download_speed / 1_000_000, 2)  # Convert to Mbps

                # Perform upload test
                upload_speed = st.upload()
                result['upload_speed'] = round(upload_speed / 1_000_000, 2)  # Convert to Mbps

                result['is_successful'] = True

        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"Speed test error: {str(e)}")

        result['test_duration'] = time.time() - start_time
        return result
