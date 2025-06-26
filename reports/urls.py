"""
URL configuration for reports app
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.index, name='index'),
    path('device-status/', views.device_status_report, name='device_status'),
    path('uptime/', views.uptime_report, name='uptime'),
]
