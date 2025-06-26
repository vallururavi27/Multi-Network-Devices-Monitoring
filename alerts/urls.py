"""
URL configuration for alerts app
"""
from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.list_alerts, name='list'),
    path('<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge'),
    path('<int:alert_id>/resolve/', views.resolve_alert, name='resolve'),
]
