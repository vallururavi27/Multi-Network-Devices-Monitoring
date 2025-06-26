"""
Reports models for network monitoring
"""
from django.db import models
from django.contrib.auth.models import User


class Report(models.Model):
    """Model for storing generated reports"""
    
    REPORT_TYPES = [
        ('device_status', 'Device Status Report'),
        ('uptime', 'Uptime Report'),
        ('performance', 'Performance Report'),
        ('alerts', 'Alerts Report'),
        ('speed_test', 'Speed Test Report'),
    ]
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    
    # Report parameters
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    device_filter = models.JSONField(default=dict, blank=True)
    
    # Generated file
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    
    # Status
    is_generated = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
    
    def __str__(self):
        return self.name
