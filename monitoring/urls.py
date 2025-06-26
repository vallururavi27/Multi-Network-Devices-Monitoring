"""
URL configuration for monitoring app
"""
from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('live/', views.live_monitor, name='live'),
    path('device/<int:device_id>/', views.device_detail, name='device_detail'),
    path('sessions/', views.monitoring_sessions, name='sessions'),
    path('health/', views.system_health, name='system_health'),
    
    # API endpoints
    path('api/dashboard/', views.api_dashboard_data, name='api_dashboard_data'),
    path('api/device/<int:device_id>/', views.api_device_status, name='api_device_status'),
    path('api/test/<int:device_id>/', views.test_device, name='test_device'),
]
