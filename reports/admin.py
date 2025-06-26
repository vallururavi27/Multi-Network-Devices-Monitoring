from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'is_generated', 'generated_at', 'created_at']
    list_filter = ['report_type', 'is_generated', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['generated_at', 'created_at']
