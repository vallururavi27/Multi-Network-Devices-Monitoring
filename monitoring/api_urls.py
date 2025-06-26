"""
API URL configuration for monitoring app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API router for ViewSets (if we add them later)
router = DefaultRouter()

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Custom API endpoints
    path('dashboard/', views.api_dashboard_data, name='api_dashboard'),
    path('device/<int:device_id>/', views.api_device_status, name='api_device_status'),
    path('device/<int:device_id>/alerts/', views.get_device_alerts, name='api_device_alerts'),

    # Device testing endpoints
    path('test/<int:device_id>/', views.test_device, name='api_test_device'),
    path('speed-test/<int:device_id>/', views.run_speed_test, name='api_speed_test'),
    path('traceroute/<int:device_id>/', views.run_traceroute, name='api_traceroute'),

    # Network discovery
    path('discover/', views.discover_network, name='api_discover_network'),

    # Health check
    path('health/', views.system_health, name='api_health'),
]
