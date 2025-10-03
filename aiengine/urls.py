"""
URL configuration for the AI Engine application.

This module defines the URL patterns for testing and interacting with the WhatsApp AI agent service.
"""

from django.urls import path
from . import views

app_name = 'aiengine'

urlpatterns = [
    # Agent testing interface
    path('test/', views.AgentTestView.as_view(), name='agent_test'),
    
    # Agent status endpoint
    path('status/', views.agent_status_view, name='agent_status'),
    
    # API endpoint for external testing (no authentication required)
    path('api/test/', views.agent_test_api, name='agent_test_api'),
]
