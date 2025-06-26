"""
Django admin configuration for devices app
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Device, DeviceGroup, DeviceCredential


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'ip_address', 'device_type', 'status_badge', 'location', 
        'ping_enabled', 'alert_enabled', 'is_active', 'last_seen', 'created_at'
    ]
    list_filter = [
        'status', 'device_type', 'ping_enabled', 'speed_test_enabled', 
        'alert_enabled', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'ip_address', 'description', 'location']
    readonly_fields = ['status', 'last_seen', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'ip_address', 'description', 'device_type', 'location')
        }),
        ('Monitoring Configuration', {
            'fields': (
                'ping_enabled', 'ping_interval', 'ping_timeout',
                'speed_test_enabled', 'speed_test_interval'
            )
        }),
        ('Alert Configuration', {
            'fields': (
                'alert_enabled', 'alert_threshold_latency', 'alert_threshold_packet_loss'
            )
        }),
        ('Status', {
            'fields': ('status', 'last_seen', 'is_active'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['enable_monitoring', 'disable_monitoring', 'enable_alerts', 'disable_alerts']
    
    def status_badge(self, obj):
        """Display status as a colored badge"""
        color_map = {
            'online': 'success',
            'offline': 'danger',
            'warning': 'warning',
            'unknown': 'secondary',
        }
        color = color_map.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def enable_monitoring(self, request, queryset):
        """Enable monitoring for selected devices"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} devices enabled for monitoring.')
    enable_monitoring.short_description = "Enable monitoring for selected devices"
    
    def disable_monitoring(self, request, queryset):
        """Disable monitoring for selected devices"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} devices disabled from monitoring.')
    disable_monitoring.short_description = "Disable monitoring for selected devices"
    
    def enable_alerts(self, request, queryset):
        """Enable alerts for selected devices"""
        updated = queryset.update(alert_enabled=True)
        self.message_user(request, f'Alerts enabled for {updated} devices.')
    enable_alerts.short_description = "Enable alerts for selected devices"
    
    def disable_alerts(self, request, queryset):
        """Disable alerts for selected devices"""
        updated = queryset.update(alert_enabled=False)
        self.message_user(request, f'Alerts disabled for {updated} devices.')
    disable_alerts.short_description = "Disable alerts for selected devices"


@admin.register(DeviceGroup)
class DeviceGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_count_display', 'online_count_display', 'color_display', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['devices']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'color')
        }),
        ('Devices', {
            'fields': ('devices',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def device_count_display(self, obj):
        """Display device count"""
        return obj.device_count
    device_count_display.short_description = 'Device Count'
    
    def online_count_display(self, obj):
        """Display online device count"""
        return f"{obj.online_count}/{obj.device_count}"
    online_count_display.short_description = 'Online/Total'
    
    def color_display(self, obj):
        """Display color as a colored box"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'


class DeviceCredentialInline(admin.StackedInline):
    model = DeviceCredential
    extra = 0
    fields = ['username', 'password', 'ssh_key', 'snmp_community', 'snmp_version']
    
    def get_extra(self, request, obj=None, **kwargs):
        """Don't show extra forms if credentials already exist"""
        if obj and hasattr(obj, 'credentials'):
            return 0
        return 1


@admin.register(DeviceCredential)
class DeviceCredentialAdmin(admin.ModelAdmin):
    list_display = ['device', 'username', 'snmp_community', 'snmp_version', 'created_at']
    list_filter = ['snmp_version', 'created_at']
    search_fields = ['device__name', 'device__ip_address', 'username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Device', {
            'fields': ('device',)
        }),
        ('Authentication', {
            'fields': ('username', 'password', 'ssh_key')
        }),
        ('SNMP Configuration', {
            'fields': ('snmp_community', 'snmp_version')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Customize admin site
admin.site.site_header = "Network Monitor Administration"
admin.site.site_title = "Network Monitor Admin"
admin.site.index_title = "Welcome to Network Monitor Administration"
