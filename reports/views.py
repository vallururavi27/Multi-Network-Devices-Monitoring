"""
Views for reports and analytics
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from devices.models import Device
from monitoring.models import PingResult, SpeedTestResult
from alerts.models import Alert


def index(request):
    """Reports index page"""
    context = {
        'total_devices': Device.objects.filter(is_active=True).count(),
        'total_pings_today': PingResult.objects.filter(
            timestamp__date=timezone.now().date()
        ).count(),
        'total_alerts_today': Alert.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
    }
    return render(request, 'reports/index.html', context)


def device_status_report(request):
    """Device status report"""
    devices = Device.objects.filter(is_active=True).order_by('name')
    
    context = {
        'devices': devices,
        'report_type': 'Device Status Report',
    }
    return render(request, 'reports/device_status.html', context)


def uptime_report(request):
    """Uptime report"""
    days = int(request.GET.get('days', 7))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    devices = Device.objects.filter(is_active=True)
    device_data = []
    
    for device in devices:
        uptime = device.get_uptime_percentage(days)
        avg_response = device.get_average_response_time(days)
        
        device_data.append({
            'device': device,
            'uptime_percentage': uptime,
            'avg_response_time': avg_response,
        })
    
    context = {
        'device_data': device_data,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/uptime.html', context)
