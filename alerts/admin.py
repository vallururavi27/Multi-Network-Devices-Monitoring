from django.contrib import admin
from .models import Alert, AlertRule, NotificationChannel

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'device', 'severity', 'alert_type', 'is_active', 'created_at']
    list_filter = ['severity', 'alert_type', 'is_active', 'created_at']
    search_fields = ['title', 'message', 'device__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'condition_type', 'alert_severity', 'is_enabled']
    list_filter = ['condition_type', 'alert_severity', 'is_enabled']
    search_fields = ['name', 'description']

@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'is_enabled']
    list_filter = ['channel_type', 'is_enabled']
    search_fields = ['name']
