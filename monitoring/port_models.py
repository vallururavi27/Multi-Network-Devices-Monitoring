"""
Port and Service Monitoring Models
"""
from django.db import models
from django.utils import timezone
from devices.models import Device


class ServiceType(models.TextChoices):
    """Service types for monitoring"""
    HTTP = 'http', 'HTTP'
    HTTPS = 'https', 'HTTPS'
    FTP = 'ftp', 'FTP'
    SFTP = 'sftp', 'SFTP'
    SSH = 'ssh', 'SSH'
    TELNET = 'telnet', 'Telnet'
    SMTP = 'smtp', 'SMTP'
    POP3 = 'pop3', 'POP3'
    IMAP = 'imap', 'IMAP'
    DNS = 'dns', 'DNS'
    DHCP = 'dhcp', 'DHCP'
    SNMP = 'snmp', 'SNMP'
    MYSQL = 'mysql', 'MySQL'
    POSTGRESQL = 'postgresql', 'PostgreSQL'
    MSSQL = 'mssql', 'SQL Server'
    ORACLE = 'oracle', 'Oracle'
    MONGODB = 'mongodb', 'MongoDB'
    REDIS = 'redis', 'Redis'
    CUSTOM = 'custom', 'Custom'


class PortMonitor(models.Model):
    """Model for monitoring specific ports on devices"""
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='port_monitors')
    port = models.PositiveIntegerField(help_text="Port number to monitor")
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.CUSTOM,
        help_text="Type of service running on this port"
    )
    service_name = models.CharField(max_length=100, blank=True, help_text="Custom service name")
    
    # Monitoring settings
    is_enabled = models.BooleanField(default=True, help_text="Enable monitoring for this port")
    check_interval = models.PositiveIntegerField(default=300, help_text="Check interval in seconds")
    timeout = models.PositiveIntegerField(default=10, help_text="Connection timeout in seconds")
    
    # Alert settings
    alert_on_failure = models.BooleanField(default=True, help_text="Send alert when port is unreachable")
    alert_threshold = models.PositiveIntegerField(default=3, help_text="Number of failures before alert")
    
    # Status tracking
    is_reachable = models.BooleanField(default=True, help_text="Current reachability status")
    last_check = models.DateTimeField(null=True, blank=True, help_text="Last check timestamp")
    last_success = models.DateTimeField(null=True, blank=True, help_text="Last successful check")
    consecutive_failures = models.PositiveIntegerField(default=0, help_text="Consecutive failure count")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['device', 'port']
        ordering = ['device', 'port']
        verbose_name = 'Port Monitor'
        verbose_name_plural = 'Port Monitors'
        indexes = [
            models.Index(fields=['device', 'port']),
            models.Index(fields=['is_enabled', 'last_check']),
            models.Index(fields=['service_type']),
        ]
    
    def __str__(self):
        service_name = self.service_name or self.get_service_type_display()
        return f"{self.device.name}:{self.port} ({service_name})"
    
    @property
    def status_color(self):
        """Get Bootstrap color class for status"""
        if not self.is_enabled:
            return 'secondary'
        elif self.is_reachable:
            return 'success'
        elif self.consecutive_failures >= self.alert_threshold:
            return 'danger'
        else:
            return 'warning'
    
    @property
    def status_icon(self):
        """Get Bootstrap icon for status"""
        if not self.is_enabled:
            return 'bi-pause-circle'
        elif self.is_reachable:
            return 'bi-check-circle-fill'
        else:
            return 'bi-x-circle-fill'


class PortCheckResult(models.Model):
    """Model for storing port check results"""
    
    port_monitor = models.ForeignKey(PortMonitor, on_delete=models.CASCADE, related_name='check_results')
    
    # Check results
    is_reachable = models.BooleanField(help_text="Whether the port was reachable")
    response_time = models.FloatField(null=True, blank=True, help_text="Response time in milliseconds")
    error_message = models.TextField(blank=True, help_text="Error message if check failed")
    
    # Service-specific data
    http_status_code = models.PositiveIntegerField(null=True, blank=True, help_text="HTTP status code")
    http_response_size = models.PositiveIntegerField(null=True, blank=True, help_text="HTTP response size in bytes")
    ssl_cert_expiry = models.DateTimeField(null=True, blank=True, help_text="SSL certificate expiry date")
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Port Check Result'
        verbose_name_plural = 'Port Check Results'
        indexes = [
            models.Index(fields=['port_monitor', '-timestamp']),
            models.Index(fields=['-timestamp']),
            models.Index(fields=['is_reachable']),
        ]
    
    def __str__(self):
        status = "Success" if self.is_reachable else "Failed"
        return f"{self.port_monitor} - {status} at {self.timestamp}"
    
    @property
    def status_color(self):
        """Get Bootstrap color class for status"""
        return 'success' if self.is_reachable else 'danger'


class ServiceMonitor(models.Model):
    """Model for monitoring specific services with custom checks"""
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='service_monitors')
    service_name = models.CharField(max_length=100, help_text="Service name")
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        help_text="Type of service"
    )
    
    # Connection details
    port = models.PositiveIntegerField(help_text="Service port")
    protocol = models.CharField(max_length=10, default='tcp', choices=[('tcp', 'TCP'), ('udp', 'UDP')])
    
    # Service-specific settings
    url_path = models.CharField(max_length=500, blank=True, help_text="URL path for HTTP checks")
    expected_response = models.TextField(blank=True, help_text="Expected response content")
    username = models.CharField(max_length=100, blank=True, help_text="Username for authentication")
    password = models.CharField(max_length=100, blank=True, help_text="Password for authentication")
    
    # Monitoring settings
    is_enabled = models.BooleanField(default=True)
    check_interval = models.PositiveIntegerField(default=300, help_text="Check interval in seconds")
    timeout = models.PositiveIntegerField(default=30, help_text="Check timeout in seconds")
    
    # Status
    is_healthy = models.BooleanField(default=True)
    last_check = models.DateTimeField(null=True, blank=True)
    last_success = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['device', 'service_name']
        ordering = ['device', 'service_name']
        verbose_name = 'Service Monitor'
        verbose_name_plural = 'Service Monitors'
    
    def __str__(self):
        return f"{self.device.name} - {self.service_name}"


class ServiceCheckResult(models.Model):
    """Model for storing service check results"""
    
    service_monitor = models.ForeignKey(ServiceMonitor, on_delete=models.CASCADE, related_name='check_results')
    
    # Check results
    is_healthy = models.BooleanField()
    response_time = models.FloatField(null=True, blank=True, help_text="Response time in milliseconds")
    status_message = models.TextField(blank=True)
    error_details = models.TextField(blank=True)
    
    # Service-specific metrics
    metrics_data = models.JSONField(default=dict, blank=True, help_text="Service-specific metrics")
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Service Check Result'
        verbose_name_plural = 'Service Check Results'
        indexes = [
            models.Index(fields=['service_monitor', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        status = "Healthy" if self.is_healthy else "Unhealthy"
        return f"{self.service_monitor.service_name} - {status}"


# Common port mappings for auto-detection
COMMON_PORTS = {
    21: ServiceType.FTP,
    22: ServiceType.SSH,
    23: ServiceType.TELNET,
    25: ServiceType.SMTP,
    53: ServiceType.DNS,
    80: ServiceType.HTTP,
    110: ServiceType.POP3,
    143: ServiceType.IMAP,
    161: ServiceType.SNMP,
    443: ServiceType.HTTPS,
    993: ServiceType.IMAP,
    995: ServiceType.POP3,
    1433: ServiceType.MSSQL,
    3306: ServiceType.MYSQL,
    5432: ServiceType.POSTGRESQL,
    1521: ServiceType.ORACLE,
    27017: ServiceType.MONGODB,
    6379: ServiceType.REDIS,
    8080: ServiceType.HTTP,
    8443: ServiceType.HTTPS,
}


def get_service_type_for_port(port):
    """Get the most likely service type for a given port"""
    return COMMON_PORTS.get(port, ServiceType.CUSTOM)
