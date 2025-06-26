from datetime import datetime, timedelta
from app import db
from sqlalchemy import Index
from enum import Enum

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
    ip_address = db.Column(db.String(45), nullable=False, unique=True)  # IPv4/IPv6
    description = db.Column(db.Text)
    device_type = db.Column(db.String(50), default='server')  # server, router, switch, etc.
    location = db.Column(db.String(100))
    
    # Monitoring configuration
    ping_enabled = db.Column(db.Boolean, default=True)
    ping_interval = db.Column(db.Integer, default=60)  # seconds
    ping_timeout = db.Column(db.Integer, default=5)  # seconds
    speed_test_enabled = db.Column(db.Boolean, default=False)
    speed_test_interval = db.Column(db.Integer, default=3600)  # seconds
    
    # Alert configuration
    alert_enabled = db.Column(db.Boolean, default=True)
    alert_threshold_latency = db.Column(db.Float, default=1000.0)  # milliseconds
    alert_threshold_packet_loss = db.Column(db.Float, default=10.0)  # percentage
    
    # Status and metadata
    status = db.Column(db.Enum(DeviceStatus), default=DeviceStatus.UNKNOWN)
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    ping_results = db.relationship('PingResult', backref='device', lazy='dynamic', cascade='all, delete-orphan')
    speed_results = db.relationship('SpeedTestResult', backref='device', lazy='dynamic', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='device', lazy='dynamic', cascade='all, delete-orphan')
    
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

# Create composite index for efficient queries
Index('idx_ping_device_timestamp', PingResult.device_id, PingResult.timestamp)

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
    severity = db.Column(db.String(20), default='medium')  # low, medium, high, critical
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

class MonitoringSession(db.Model):
    """Monitoring session model for tracking monitoring periods."""
    __tablename__ = 'monitoring_sessions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # Session configuration
    devices = db.Column(db.Text)  # JSON string of device IDs
    ping_interval = db.Column(db.Integer, default=60)
    speed_test_interval = db.Column(db.Integer, default=3600)

    # Session status
    is_active = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime)
    stopped_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))

    def __repr__(self):
        return f'<MonitoringSession {self.name}>'

class SystemSettings(db.Model):
    """System settings model for application configuration."""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, integer, float, boolean, json
    is_sensitive = db.Column(db.Boolean, default=False)  # For passwords, API keys, etc.

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
            import json
            return json.loads(self.value) if self.value else {}
        else:
            return self.value or ''

# Create additional indexes for performance
Index('idx_speed_device_timestamp', SpeedTestResult.device_id, SpeedTestResult.timestamp)
Index('idx_alert_device_created', Alert.device_id, Alert.created_at)
Index('idx_alert_active', Alert.is_active, Alert.created_at)
