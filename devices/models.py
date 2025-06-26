"""
Device models for network monitoring
"""
from django.db import models
from django.core.validators import validate_ipv4_address, MinValueValidator, MaxValueValidator
from django.urls import reverse
import ipaddress


class DeviceStatus(models.TextChoices):
    """Device status choices"""
    ONLINE = 'online', 'Online'
    OFFLINE = 'offline', 'Offline'
    WARNING = 'warning', 'Warning'
    UNKNOWN = 'unknown', 'Unknown'


class DeviceType(models.TextChoices):
    """Device type choices"""
    SERVER = 'server', 'Server'
    ROUTER = 'router', 'Router'
    SWITCH = 'switch', 'Switch'
    FIREWALL = 'firewall', 'Firewall'
    PRINTER = 'printer', 'Printer'
    WORKSTATION = 'workstation', 'Workstation'
    DNS_SERVER = 'dns_server', 'DNS Server'
    WEB_SERVER = 'web_server', 'Web Server'
    DATABASE = 'database', 'Database'
    FTP_SERVER = 'ftp_server', 'FTP Server'
    LOAD_BALANCER = 'load_balancer', 'Load Balancer'
    OTHER = 'other', 'Other'


class Device(models.Model):
    """Device model for storing monitored devices"""

    # Basic Information
    name = models.CharField(max_length=100, help_text="Friendly name for the device")
    ip_address = models.GenericIPAddressField(
        unique=True,
        validators=[validate_ipv4_address],
        help_text="IPv4 address of the device"
    )
    hostname = models.CharField(max_length=255, blank=True, help_text="Device hostname")
    description = models.TextField(blank=True, help_text="Optional description")
    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.SERVER,
        help_text="Type of device"
    )

    # Location and Network Information
    location = models.CharField(max_length=100, blank=True, help_text="Physical or logical location")
    country = models.CharField(max_length=100, blank=True, help_text="Country")
    city = models.CharField(max_length=100, blank=True, help_text="City")
    isp = models.CharField(max_length=200, blank=True, help_text="Internet Service Provider")
    organization = models.CharField(max_length=200, blank=True, help_text="Organization")

    # Geographic Coordinates
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, help_text="Longitude coordinate")

    # Network Performance Metrics
    current_latency = models.FloatField(null=True, blank=True, help_text="Current latency in ms")
    current_upload_speed = models.FloatField(null=True, blank=True, help_text="Current upload speed in Mbps")
    current_download_speed = models.FloatField(null=True, blank=True, help_text="Current download speed in Mbps")

    # Traceroute Information
    traceroute_hops = models.JSONField(default=list, blank=True, help_text="Traceroute hop information")
    last_traceroute = models.DateTimeField(null=True, blank=True, help_text="Last traceroute execution")
    
    # Monitoring Configuration
    ping_enabled = models.BooleanField(default=True, help_text="Enable ping monitoring")
    ping_interval = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(30), MaxValueValidator(3600)],
        help_text="Ping interval in seconds (30-3600)"
    )
    ping_timeout = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Ping timeout in seconds (1-30)"
    )
    
    # Speed Test Configuration
    speed_test_enabled = models.BooleanField(default=False, help_text="Enable speed testing")
    speed_test_interval = models.PositiveIntegerField(
        default=3600,
        validators=[MinValueValidator(300), MaxValueValidator(86400)],
        help_text="Speed test interval in seconds (300-86400)"
    )
    
    # Alert Configuration
    alert_enabled = models.BooleanField(default=True, help_text="Enable alerts for this device")
    alert_threshold_latency = models.FloatField(
        default=1000.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(10000.0)],
        help_text="Alert threshold for latency in milliseconds"
    )
    alert_threshold_packet_loss = models.FloatField(
        default=10.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Alert threshold for packet loss percentage"
    )
    
    # Status and Metadata
    status = models.CharField(
        max_length=10,
        choices=DeviceStatus.choices,
        default=DeviceStatus.UNKNOWN,
        help_text="Current device status"
    )
    last_seen = models.DateTimeField(null=True, blank=True, help_text="Last time device was reachable")
    is_active = models.BooleanField(default=True, help_text="Whether monitoring is active")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
            models.Index(fields=['device_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.ip_address})"
    
    def get_absolute_url(self):
        return reverse('devices:detail', kwargs={'pk': self.pk})
    
    def clean(self):
        """Validate the device data"""
        super().clean()
        
        # Validate IP address format
        try:
            ipaddress.ip_address(self.ip_address)
        except ValueError:
            from django.core.exceptions import ValidationError
            raise ValidationError({'ip_address': 'Invalid IP address format'})
    
    @property
    def status_color(self):
        """Return Bootstrap color class for status"""
        color_map = {
            DeviceStatus.ONLINE: 'success',
            DeviceStatus.OFFLINE: 'danger',
            DeviceStatus.WARNING: 'warning',
            DeviceStatus.UNKNOWN: 'secondary',
        }
        return color_map.get(self.status, 'secondary')
    
    @property
    def status_icon(self):
        """Return Bootstrap icon for status"""
        icon_map = {
            DeviceStatus.ONLINE: 'bi-check-circle-fill',
            DeviceStatus.OFFLINE: 'bi-x-circle-fill',
            DeviceStatus.WARNING: 'bi-exclamation-triangle-fill',
            DeviceStatus.UNKNOWN: 'bi-question-circle-fill',
        }
        return icon_map.get(self.status, 'bi-question-circle-fill')
    
    def get_recent_ping_results(self, limit=10):
        """Get recent ping results for this device"""
        return self.ping_results.order_by('-timestamp')[:limit]
    
    def get_recent_speed_results(self, limit=5):
        """Get recent speed test results for this device"""
        return self.speed_results.order_by('-timestamp')[:limit]
    
    def get_uptime_percentage(self, days=1):
        """Calculate uptime percentage for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)
        
        ping_results = self.ping_results.filter(
            timestamp__gte=start_time,
            timestamp__lte=end_time
        )
        
        total_pings = ping_results.count()
        if total_pings == 0:
            return None
        
        successful_pings = ping_results.filter(is_reachable=True).count()
        return round((successful_pings / total_pings) * 100, 2)
    
    def get_average_response_time(self, days=1):
        """Calculate average response time for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Avg
        
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)
        
        avg_response = self.ping_results.filter(
            timestamp__gte=start_time,
            timestamp__lte=end_time,
            is_reachable=True,
            response_time__isnull=False
        ).aggregate(avg_time=Avg('response_time'))
        
        return round(avg_response['avg_time'], 2) if avg_response['avg_time'] else None


class DeviceGroup(models.Model):
    """Device group model for organizing devices"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    devices = models.ManyToManyField(Device, related_name='groups', blank=True)
    color = models.CharField(
        max_length=7,
        default='#007bff',
        help_text="Hex color code for group visualization"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Device Group'
        verbose_name_plural = 'Device Groups'
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('devices:group_detail', kwargs={'pk': self.pk})
    
    @property
    def device_count(self):
        """Return number of devices in this group"""
        return self.devices.count()
    
    @property
    def online_count(self):
        """Return number of online devices in this group"""
        return self.devices.filter(status=DeviceStatus.ONLINE).count()
    
    @property
    def offline_count(self):
        """Return number of offline devices in this group"""
        return self.devices.filter(status=DeviceStatus.OFFLINE).count()


class DeviceCredential(models.Model):
    """Store device credentials for advanced monitoring"""
    
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='credentials')
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=255, blank=True)  # Should be encrypted in production
    ssh_key = models.TextField(blank=True, help_text="SSH private key for authentication")
    snmp_community = models.CharField(max_length=100, blank=True, default='public')
    snmp_version = models.CharField(
        max_length=10,
        choices=[('v1', 'v1'), ('v2c', 'v2c'), ('v3', 'v3')],
        default='v2c'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Device Credential'
        verbose_name_plural = 'Device Credentials'
    
    def __str__(self):
        return f"Credentials for {self.device.name}"
