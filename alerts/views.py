"""
Views for alert management
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Alert


def list_alerts(request):
    """List all alerts with filtering"""
    alerts = Alert.objects.select_related('device').order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        alerts = alerts.filter(is_active=True)
    elif status_filter == 'resolved':
        alerts = alerts.filter(is_active=False)
    
    severity_filter = request.GET.get('severity')
    if severity_filter:
        alerts = alerts.filter(severity=severity_filter)
    
    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'severity_filter': severity_filter,
    }
    return render(request, 'alerts/list.html', context)


def acknowledge_alert(request, alert_id):
    """Acknowledge an alert"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    if request.method == 'POST':
        alert.acknowledge(acknowledged_by='User')
        messages.success(request, f'Alert "{alert.title}" has been acknowledged.')
        return redirect('alerts:list')
    
    return JsonResponse({'error': 'POST method required'}, status=405)


def resolve_alert(request, alert_id):
    """Resolve an alert"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    if request.method == 'POST':
        alert.resolve()
        messages.success(request, f'Alert "{alert.title}" has been resolved.')
        return redirect('alerts:list')
    
    return JsonResponse({'error': 'POST method required'}, status=405)
