"""
Monitoring models for network monitoring results
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
from devices.models import Device


class PingResult(models.Model):
    """Model for storing ping test results"""
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='ping_results')
    
    # Ping metrics
    is_reachable = models.BooleanField(help_text="Whether the device responded to ping")
    response_time = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Response time in milliseconds"
    )
    packet_loss = models.FloatField(
        default=0.0, 
        help_text="Packet loss percentage"
    )
    packets_sent = models.PositiveIntegerField(default=4, help_text="Number of packets sent")
    packets_received = models.PositiveIntegerField(default=0, help_text="Number of packets received")
    
    # Additional metrics
    min_time = models.FloatField(null=True, blank=True, help_text="Minimum response time")
    max_time = models.FloatField(null=True, blank=True, help_text="Maximum response time")
    avg_time = models.FloatField(null=True, blank=True, help_text="Average response time")
    
    # Error information
    error_message = models.TextField(blank=True, help_text="Error message if ping failed")
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Ping Result'
        verbose_name_plural = 'Ping Results'
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['is_reachable', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        status = "Success" if self.is_reachable else "Failed"
        return f"{self.device.name} - {status} at {self.timestamp}"
    
    @property
    def status_color(self):
        """Return Bootstrap color class for status"""
        return 'success' if self.is_reachable else 'danger'
    
    @property
    def status_icon(self):
        """Return Bootstrap icon for status"""
        return 'bi-check-circle-fill' if self.is_reachable else 'bi-x-circle-fill'


class SpeedTestResult(models.Model):
    """Model for storing network speed test results"""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='speed_results')

    # Speed test metrics
    download_speed = models.FloatField(null=True, blank=True, help_text="Download speed in Mbps")
    upload_speed = models.FloatField(null=True, blank=True, help_text="Upload speed in Mbps")
    ping_latency = models.FloatField(null=True, blank=True, help_text="Ping latency in milliseconds")
    jitter = models.FloatField(null=True, blank=True, help_text="Jitter in milliseconds")
    packet_loss_percent = models.FloatField(null=True, blank=True, help_text="Packet loss percentage")
    
    # Server information
    server_name = models.CharField(max_length=100, blank=True, help_text="Speed test server name")
    server_location = models.CharField(max_length=100, blank=True, help_text="Speed test server location")
    server_country = models.CharField(max_length=50, blank=True, help_text="Speed test server country")
    server_sponsor = models.CharField(max_length=100, blank=True, help_text="Speed test server sponsor")
    server_id = models.CharField(max_length=20, blank=True, help_text="Speed test server ID")
    
    # Client information
    client_ip = models.GenericIPAddressField(null=True, blank=True, help_text="Client IP address")
    client_isp = models.CharField(max_length=100, blank=True, help_text="Client ISP")
    
    # Test metadata
    test_duration = models.FloatField(null=True, blank=True, help_text="Test duration in seconds")
    is_successful = models.BooleanField(default=True, help_text="Whether the test completed successfully")
    error_message = models.TextField(blank=True, help_text="Error message if test failed")
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Speed Test Result'
        verbose_name_plural = 'Speed Test Results'
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['is_successful', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        if self.is_successful:
            return f"{self.device.name} - {self.download_speed}↓/{self.upload_speed}↑ Mbps"
        return f"{self.device.name} - Speed test failed"
    
    @property
    def status_color(self):
        """Return Bootstrap color class for status"""
        return 'success' if self.is_successful else 'danger'
    
    @property
    def download_speed_formatted(self):
        """Return formatted download speed"""
        if self.download_speed is None:
            return "N/A"
        return f"{self.download_speed:.1f} Mbps"
    
    @property
    def upload_speed_formatted(self):
        """Return formatted upload speed"""
        if self.upload_speed is None:
            return "N/A"
        return f"{self.upload_speed:.1f} Mbps"


class MonitoringSession(models.Model):
    """Model for tracking monitoring sessions"""
    
    name = models.CharField(max_length=100, help_text="Session name")
    description = models.TextField(blank=True, help_text="Session description")
    
    # Session configuration
    devices = models.ManyToManyField(Device, related_name='monitoring_sessions')
    ping_interval = models.PositiveIntegerField(default=60, help_text="Ping interval in seconds")
    speed_test_interval = models.PositiveIntegerField(default=3600, help_text="Speed test interval in seconds")
    
    # Session status
    is_active = models.BooleanField(default=False, help_text="Whether the session is active")
    started_at = models.DateTimeField(null=True, blank=True, help_text="When the session started")
    stopped_at = models.DateTimeField(null=True, blank=True, help_text="When the session stopped")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User who created the session"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Monitoring Session'
        verbose_name_plural = 'Monitoring Sessions'
    
    def __str__(self):
        return self.name
    
    @property
    def duration(self):
        """Return session duration"""
        if self.started_at:
            end_time = self.stopped_at or timezone.now()
            return end_time - self.started_at
        return None
    
    @property
    def device_count(self):
        """Return number of devices in session"""
        return self.devices.count()
    
    def start_session(self):
        """Start the monitoring session"""
        self.is_active = True
        self.started_at = timezone.now()
        self.stopped_at = None
        self.save()
    
    def stop_session(self):
        """Stop the monitoring session"""
        self.is_active = False
        self.stopped_at = timezone.now()
        self.save()


class SystemMetrics(models.Model):
    """Model for storing system-wide monitoring metrics"""
    
    # Device counts
    total_devices = models.PositiveIntegerField(default=0)
    online_devices = models.PositiveIntegerField(default=0)
    offline_devices = models.PositiveIntegerField(default=0)
    warning_devices = models.PositiveIntegerField(default=0)
    
    # Monitoring statistics
    total_pings_today = models.PositiveIntegerField(default=0)
    successful_pings_today = models.PositiveIntegerField(default=0)
    total_speed_tests_today = models.PositiveIntegerField(default=0)
    successful_speed_tests_today = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    avg_response_time = models.FloatField(null=True, blank=True)
    avg_download_speed = models.FloatField(null=True, blank=True)
    avg_upload_speed = models.FloatField(null=True, blank=True)
    
    # System health
    monitoring_active = models.BooleanField(default=True)
    last_monitoring_run = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    date = models.DateField(auto_now_add=True, unique=True)
    timestamp = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'System Metrics'
        verbose_name_plural = 'System Metrics'
    
    def __str__(self):
        return f"System Metrics for {self.date}"
    
    @property
    def uptime_percentage(self):
        """Calculate overall uptime percentage"""
        if self.total_pings_today == 0:
            return 0
        return round((self.successful_pings_today / self.total_pings_today) * 100, 2)
    
    @property
    def speed_test_success_rate(self):
        """Calculate speed test success rate"""
        if self.total_speed_tests_today == 0:
            return 0
        return round((self.successful_speed_tests_today / self.total_speed_tests_today) * 100, 2)
    
    @classmethod
    def get_or_create_today(cls):
        """Get or create today's metrics"""
        today = timezone.now().date()
        metrics, created = cls.objects.get_or_create(date=today)
        return metrics
    
    def update_device_counts(self):
        """Update device counts from current device statuses"""
        from devices.models import DeviceStatus
        
        devices = Device.objects.filter(is_active=True)
        self.total_devices = devices.count()
        self.online_devices = devices.filter(status=DeviceStatus.ONLINE).count()
        self.offline_devices = devices.filter(status=DeviceStatus.OFFLINE).count()
        self.warning_devices = devices.filter(status=DeviceStatus.WARNING).count()
        self.save()
    
    def update_ping_stats(self):
        """Update ping statistics for today"""
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        ping_results = PingResult.objects.filter(
            timestamp__gte=today,
            timestamp__lt=tomorrow
        )
        
        self.total_pings_today = ping_results.count()
        self.successful_pings_today = ping_results.filter(is_reachable=True).count()
        
        # Calculate average response time
        successful_pings = ping_results.filter(is_reachable=True, response_time__isnull=False)
        if successful_pings.exists():
            from django.db.models import Avg
            avg_time = successful_pings.aggregate(avg=Avg('response_time'))['avg']
            self.avg_response_time = round(avg_time, 2) if avg_time else None
        
        self.save()
    
    def update_speed_test_stats(self):
        """Update speed test statistics for today"""
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        speed_results = SpeedTestResult.objects.filter(
            timestamp__gte=today,
            timestamp__lt=tomorrow
        )
        
        self.total_speed_tests_today = speed_results.count()
        self.successful_speed_tests_today = speed_results.filter(is_successful=True).count()
        
        # Calculate average speeds
        successful_tests = speed_results.filter(is_successful=True)
        if successful_tests.exists():
            from django.db.models import Avg
            
            download_avg = successful_tests.filter(download_speed__isnull=False).aggregate(
                avg=Avg('download_speed')
            )['avg']
            upload_avg = successful_tests.filter(upload_speed__isnull=False).aggregate(
                avg=Avg('upload_speed')
            )['avg']
            
            self.avg_download_speed = round(download_avg, 2) if download_avg else None
            self.avg_upload_speed = round(upload_avg, 2) if upload_avg else None
        
        self.save()


class TracerouteResult(models.Model):
    """Model for storing traceroute results"""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='traceroute_results')

    # Traceroute data
    hops = models.JSONField(default=list, help_text="List of traceroute hops")
    total_hops = models.PositiveIntegerField(default=0, help_text="Total number of hops")
    destination_reached = models.BooleanField(default=False, help_text="Whether destination was reached")
    total_time = models.FloatField(null=True, blank=True, help_text="Total time to reach destination")

    # Error information
    error_message = models.TextField(blank=True, help_text="Error message if traceroute failed")
    is_successful = models.BooleanField(default=True, help_text="Whether traceroute completed successfully")

    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Traceroute Result'
        verbose_name_plural = 'Traceroute Results'
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        status = "Success" if self.is_successful else "Failed"
        return f"Traceroute to {self.device.name} - {status}"


class GeoLocation(models.Model):
    """Model for storing IP geolocation data"""

    ip_address = models.GenericIPAddressField(unique=True)

    # Location data
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    region = models.CharField(max_length=100, blank=True)
    region_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Coordinates
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Network information
    isp = models.CharField(max_length=200, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    asn = models.CharField(max_length=50, blank=True, help_text="Autonomous System Number")

    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Geo Location'
        verbose_name_plural = 'Geo Locations'
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['country']),
            models.Index(fields=['isp']),
        ]

    def __str__(self):
        location_parts = [self.city, self.region, self.country]
        location = ', '.join(filter(None, location_parts))
        return f"{self.ip_address} - {location}"


# Import port monitoring models
from .port_models import (
    ServiceType, PortMonitor, PortCheckResult,
    ServiceMonitor, ServiceCheckResult,
    COMMON_PORTS, get_service_type_for_port
)
