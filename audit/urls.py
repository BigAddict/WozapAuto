from django.urls import path

from . import views

app_name = 'audit'

urlpatterns = [
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:pk>/detail/', views.notification_detail, name='notification_detail'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('api/analytics/', views.analytics_api, name='analytics_api'),
]


