"""
Alert models for network monitoring
"""
from django.db import models
from django.utils import timezone
from devices.models import Device


class AlertType(models.TextChoices):
    """Alert type choices"""
    DEVICE_DOWN = 'device_down', 'Device Down'
    DEVICE_UP = 'device_up', 'Device Up'
    HIGH_LATENCY = 'high_latency', 'High Latency'
    SPEED_DEGRADATION = 'speed_degradation', 'Speed Degradation'
    TIMEOUT = 'timeout', 'Timeout'


class AlertSeverity(models.TextChoices):
    """Alert severity choices"""
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class Alert(models.Model):
    """Alert model for storing alert notifications"""
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='alerts')
    
    # Alert details
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    severity = models.CharField(max_length=10, choices=AlertSeverity.choices, default=AlertSeverity.MEDIUM)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Alert status
    is_active = models.BooleanField(default=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.CharField(max_length=100, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Notification tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        indexes = [
            models.Index(fields=['device', '-created_at']),
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.device.name}"
    
    @property
    def severity_color(self):
        """Return Bootstrap color class for severity"""
        color_map = {
            AlertSeverity.LOW: 'info',
            AlertSeverity.MEDIUM: 'warning',
            AlertSeverity.HIGH: 'danger',
            AlertSeverity.CRITICAL: 'dark',
        }
        return color_map.get(self.severity, 'secondary')
    
    @property
    def severity_icon(self):
        """Return Bootstrap icon for severity"""
        icon_map = {
            AlertSeverity.LOW: 'bi-info-circle',
            AlertSeverity.MEDIUM: 'bi-exclamation-triangle',
            AlertSeverity.HIGH: 'bi-exclamation-octagon',
            AlertSeverity.CRITICAL: 'bi-x-octagon',
        }
        return icon_map.get(self.severity, 'bi-bell')
    
    def acknowledge(self, acknowledged_by=None):
        """Acknowledge the alert"""
        self.is_acknowledged = True
        self.acknowledged_by = acknowledged_by or 'System'
        self.acknowledged_at = timezone.now()
        self.save()
    
    def resolve(self):
        """Resolve the alert"""
        self.is_active = False
        self.resolved_at = timezone.now()
        self.save()


class AlertRule(models.Model):
    """Alert rule model for defining custom alert conditions"""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Rule conditions
    device_filter = models.JSONField(default=dict, help_text="Device filter criteria")
    condition_type = models.CharField(
        max_length=20,
        choices=[
            ('ping_failure', 'Ping Failure'),
            ('high_latency', 'High Latency'),
            ('packet_loss', 'Packet Loss'),
            ('speed_degradation', 'Speed Degradation'),
        ]
    )
    threshold_value = models.FloatField(help_text="Threshold value for the condition")
    threshold_duration = models.PositiveIntegerField(
        default=300,
        help_text="Duration in seconds before triggering alert"
    )
    
    # Alert configuration
    alert_severity = models.CharField(max_length=10, choices=AlertSeverity.choices)
    alert_message_template = models.TextField(
        help_text="Alert message template (supports variables)"
    )
    
    # Rule status
    is_enabled = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'
    
    def __str__(self):
        return self.name


class NotificationChannel(models.Model):
    """Notification channel model for different alert delivery methods"""
    
    CHANNEL_TYPES = [
        ('email', 'Email'),
        ('slack', 'Slack'),
        ('webhook', 'Webhook'),
        ('sms', 'SMS'),
    ]
    
    name = models.CharField(max_length=100)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    configuration = models.JSONField(default=dict, help_text="Channel-specific configuration")
    
    # Channel status
    is_enabled = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Notification Channel'
        verbose_name_plural = 'Notification Channels'
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"
