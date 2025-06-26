"""
URL configuration for devices app
"""
from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    path('', views.device_list, name='list'),
    path('add/', views.device_add, name='add'),
    path('<int:pk>/', views.device_detail, name='detail'),
    path('<int:pk>/edit/', views.device_edit, name='edit'),
    path('<int:pk>/delete/', views.device_delete, name='delete'),
    path('import/', views.device_import, name='import'),
    path('export/', views.device_export, name='export'),
    path('map/', views.device_map, name='map'),

    # API endpoints
    path('api/map/', views.device_map_api, name='map_api'),
    path('groups/', views.group_list, name='group_list'),
    path('groups/add/', views.group_add, name='group_add'),
    path('groups/<int:pk>/', views.group_detail, name='group_detail'),
]
