"""
Views for network monitoring dashboard and live monitoring
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta, datetime
import json

from devices.models import Device, DeviceStatus
from .models import PingResult, SpeedTestResult, SystemMetrics, MonitoringSession
from alerts.models import Alert


def dashboard(request):
    """Main dashboard view"""
    # Get device status summary optimized for 1000+ devices
    from django.core.cache import cache
    from django.db.models import Count, Avg

    # Use caching for expensive queries
    cache_key = 'dashboard_status_summary'
    status_summary = cache.get(cache_key)

    if not status_summary:
        devices = Device.objects.filter(is_active=True)

        # Use aggregation for better performance with large datasets
        status_counts = devices.aggregate(
            total=Count('id'),
            online=Count('id', filter=Q(status=DeviceStatus.ONLINE)),
            offline=Count('id', filter=Q(status=DeviceStatus.OFFLINE)),
            warning=Count('id', filter=Q(status=DeviceStatus.WARNING)),
            unknown=Count('id', filter=Q(status=DeviceStatus.UNKNOWN)),
        )

        # Calculate percentages
        total = status_counts['total'] or 1
        status_summary = {
            'total': status_counts['total'],
            'online': status_counts['online'],
            'offline': status_counts['offline'],
            'warning': status_counts['warning'],
            'unknown': status_counts['unknown'],
            'online_percentage': round((status_counts['online'] / total) * 100, 1),
            'offline_percentage': round((status_counts['offline'] / total) * 100, 1),
            'warning_percentage': round((status_counts['warning'] / total) * 100, 1),
        }

        # Cache for 30 seconds
        cache.set(cache_key, status_summary, 30)
    
    # Get recent alerts
    recent_alerts = Alert.objects.filter(is_active=True).select_related('device').order_by('-created_at')[:10]
    
    # Get recent ping results for chart (last 24 hours)
    last_24h = timezone.now() - timedelta(hours=24)
    ping_data = PingResult.objects.filter(timestamp__gte=last_24h).extra(
        select={'hour': "strftime('%%H', timestamp)"}
    ).values('hour').annotate(
        total=Count('id'),
        successful=Count('id', filter=Q(is_reachable=True))
    ).order_by('hour')
    
    # Prepare chart data
    chart_data = {
        'labels': [f"{int(item['hour']):02d}:00" for item in ping_data],
        'successful': [item['successful'] for item in ping_data],
        'failed': [item['total'] - item['successful'] for item in ping_data]
    }
    
    # Get system metrics
    try:
        system_metrics = SystemMetrics.get_or_create_today()
        system_metrics.update_device_counts()
        system_metrics.update_ping_stats()
    except Exception:
        system_metrics = None
    
    # Get recent monitoring activity
    recent_pings = PingResult.objects.select_related('device').order_by('-timestamp')[:10]
    recent_speeds = SpeedTestResult.objects.select_related('device').order_by('-timestamp')[:5]
    
    # Get recent devices for display
    recent_devices = Device.objects.filter(is_active=True).order_by('-last_seen')[:10]

    context = {
        'status_summary': status_summary,
        'recent_alerts': recent_alerts,
        'chart_data': chart_data,
        'system_metrics': system_metrics,
        'recent_pings': recent_pings,
        'recent_speeds': recent_speeds,
        'devices': recent_devices,
    }
    
    return render(request, 'monitoring/dashboard.html', context)


def live_monitor(request):
    """Live monitoring view with real-time updates"""
    devices = Device.objects.filter(is_active=True).order_by('name')
    
    # Get latest ping result for each device
    device_data = []
    for device in devices:
        latest_ping = device.ping_results.first()
        latest_speed = device.speed_results.first()
        
        device_data.append({
            'device': device,
            'latest_ping': latest_ping,
            'latest_speed': latest_speed,
            'uptime_24h': device.get_uptime_percentage(1),
            'avg_response_time': device.get_average_response_time(1),
        })
    
    context = {
        'device_data': device_data,
        'refresh_interval': 30,  # seconds
    }
    
    return render(request, 'monitoring/live.html', context)


def device_detail(request, device_id):
    """Detailed view for a specific device"""
    device = get_object_or_404(Device, id=device_id)
    
    # Get time range from request
    days = int(request.GET.get('days', 7))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Get ping results for the time range
    ping_results = device.ping_results.filter(
        timestamp__gte=start_date,
        timestamp__lte=end_date
    ).order_by('-timestamp')
    
    # Get speed test results
    speed_results = device.speed_results.filter(
        timestamp__gte=start_date,
        timestamp__lte=end_date
    ).order_by('-timestamp')
    
    # Calculate statistics
    total_pings = ping_results.count()
    successful_pings = ping_results.filter(is_reachable=True).count()
    uptime_percentage = (successful_pings / total_pings * 100) if total_pings > 0 else 0
    
    # Average response time
    avg_response_time = ping_results.filter(
        is_reachable=True,
        response_time__isnull=False
    ).aggregate(avg=Avg('response_time'))['avg']
    
    # Prepare chart data for ping results
    ping_chart_data = []
    for result in ping_results[:100]:  # Last 100 results
        ping_chart_data.append({
            'timestamp': result.timestamp.isoformat(),
            'response_time': result.response_time,
            'is_reachable': result.is_reachable
        })
    
    # Speed test chart data
    speed_chart_data = []
    for result in speed_results[:50]:  # Last 50 results
        speed_chart_data.append({
            'timestamp': result.timestamp.isoformat(),
            'download_speed': result.download_speed,
            'upload_speed': result.upload_speed,
            'ping_latency': result.ping_latency
        })
    
    context = {
        'device': device,
        'ping_results': ping_results[:50],
        'speed_results': speed_results[:20],
        'total_pings': total_pings,
        'successful_pings': successful_pings,
        'uptime_percentage': round(uptime_percentage, 2),
        'avg_response_time': round(avg_response_time, 2) if avg_response_time else None,
        'ping_chart_data': json.dumps(ping_chart_data),
        'speed_chart_data': json.dumps(speed_chart_data),
        'days': days,
    }
    
    return render(request, 'monitoring/device_detail.html', context)


def api_dashboard_data(request):
    """API endpoint for dashboard data (AJAX updates)"""
    # Get device status summary
    devices = Device.objects.filter(is_active=True)
    status_summary = {
        'total': devices.count(),
        'online': devices.filter(status=DeviceStatus.ONLINE).count(),
        'offline': devices.filter(status=DeviceStatus.OFFLINE).count(),
        'warning': devices.filter(status=DeviceStatus.WARNING).count(),
        'unknown': devices.filter(status=DeviceStatus.UNKNOWN).count(),
    }
    
    # Get active alerts count
    active_alerts = Alert.objects.filter(is_active=True).count()
    
    # Get latest ping results
    latest_pings = []
    for device in devices[:10]:
        latest_ping = device.ping_results.first()
        if latest_ping:
            latest_pings.append({
                'device_name': device.name,
                'ip_address': device.ip_address,
                'status': device.status,
                'response_time': latest_ping.response_time,
                'timestamp': latest_ping.timestamp.isoformat(),
                'is_reachable': latest_ping.is_reachable
            })
    
    return JsonResponse({
        'status_summary': status_summary,
        'active_alerts': active_alerts,
        'latest_pings': latest_pings,
        'timestamp': timezone.now().isoformat()
    })


def api_device_status(request, device_id):
    """API endpoint for individual device status"""
    device = get_object_or_404(Device, id=device_id)
    
    # Get latest results
    latest_ping = device.ping_results.first()
    latest_speed = device.speed_results.first()
    
    data = {
        'device': {
            'id': device.id,
            'name': device.name,
            'ip_address': device.ip_address,
            'status': device.status,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
        },
        'latest_ping': {
            'is_reachable': latest_ping.is_reachable if latest_ping else None,
            'response_time': latest_ping.response_time if latest_ping else None,
            'timestamp': latest_ping.timestamp.isoformat() if latest_ping else None,
        } if latest_ping else None,
        'latest_speed': {
            'download_speed': latest_speed.download_speed if latest_speed else None,
            'upload_speed': latest_speed.upload_speed if latest_speed else None,
            'timestamp': latest_speed.timestamp.isoformat() if latest_speed else None,
        } if latest_speed else None,
        'uptime_24h': device.get_uptime_percentage(1),
        'avg_response_time': device.get_average_response_time(1),
    }
    
    return JsonResponse(data)


def test_device(request, device_id):
    """Manually test a device (trigger immediate ping)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    device = get_object_or_404(Device, id=device_id)

    try:
        # Import and run the monitoring task
        from .tasks import monitor_single_device
        result = monitor_single_device.delay(device_id)

        return JsonResponse({
            'success': True,
            'message': f'Test queued for {device.name}',
            'task_id': result.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def run_speed_test(request, device_id):
    """Run speed test for a device"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    device = get_object_or_404(Device, id=device_id)

    try:
        from .tasks import run_speed_test_for_device
        result = run_speed_test_for_device.delay(device_id)

        return JsonResponse({
            'success': True,
            'message': f'Speed test started for {device.name}',
            'task_id': result.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def run_traceroute(request, device_id):
    """Run traceroute for a device"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    device = get_object_or_404(Device, id=device_id)

    try:
        from .tasks import run_traceroute_for_device
        result = run_traceroute_for_device.delay(device_id)

        # For immediate response, we'll run a quick traceroute
        import subprocess
        import platform

        system = platform.system().lower()
        if system == 'windows':
            cmd = ['tracert', '-h', '10', device.ip_address]
        else:
            cmd = ['traceroute', '-m', '10', device.ip_address]

        try:
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = process.stdout

            return JsonResponse({
                'success': True,
                'result': {
                    'output': output,
                    'device': device.name,
                    'ip_address': device.ip_address
                }
            })
        except subprocess.TimeoutExpired:
            return JsonResponse({
                'success': False,
                'error': 'Traceroute timed out'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_device_alerts(request, device_id):
    """Get alerts for a specific device"""
    device = get_object_or_404(Device, id=device_id)

    from alerts.models import Alert
    alerts = Alert.objects.filter(device=device).order_by('-created_at')[:20]

    alerts_data = []
    for alert in alerts:
        alerts_data.append({
            'id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity,
            'alert_type': alert.alert_type,
            'is_active': alert.is_active,
            'is_acknowledged': alert.is_acknowledged,
            'created_at': alert.created_at.isoformat(),
        })

    return JsonResponse({
        'device': device.name,
        'alerts': alerts_data
    })


def discover_network(request):
    """Discover devices on the network"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        subnet = request.POST.get('subnet', '192.168.1.0/24')

        from .tasks import discover_network_devices
        result = discover_network_devices.delay(subnet)

        return JsonResponse({
            'success': True,
            'message': f'Network discovery started for {subnet}',
            'task_id': result.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def monitoring_sessions(request):
    """View for managing monitoring sessions"""
    sessions = MonitoringSession.objects.all().order_by('-created_at')
    
    context = {
        'sessions': sessions,
    }
    
    return render(request, 'monitoring/sessions.html', context)


def system_health(request):
    """System health and status page"""
    # Get system metrics
    try:
        system_metrics = SystemMetrics.get_or_create_today()
        system_metrics.update_device_counts()
        system_metrics.update_ping_stats()
        system_metrics.update_speed_test_stats()
    except Exception as e:
        system_metrics = None
        messages.error(request, f"Error updating system metrics: {e}")
    
    # Get recent system metrics for trend
    recent_metrics = SystemMetrics.objects.order_by('-date')[:7]
    
    # Check system health indicators
    health_checks = {
        'database': True,  # If we got here, DB is working
        'redis': False,
        'celery_worker': False,
        'celery_beat': False,
    }
    
    # Try to check Redis connection
    try:
        import redis
        r = redis.Redis.from_url('redis://localhost:6379/0')
        r.ping()
        health_checks['redis'] = True
    except Exception:
        pass
    
    # Check Celery (simplified check)
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        if stats:
            health_checks['celery_worker'] = True
    except Exception:
        pass
    
    context = {
        'system_metrics': system_metrics,
        'recent_metrics': recent_metrics,
        'health_checks': health_checks,
    }
    
    return render(request, 'monitoring/system_health.html', context)
