from django.urls import path

from . import views

app_name = 'audit'

urlpatterns = [
    path('notifications/', views.notifications_list, name='notifications'),
]


