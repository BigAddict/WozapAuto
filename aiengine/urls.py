"""
URL configuration for the AI Engine application.

This module defines the URL patterns for testing and interacting with the WhatsApp AI agent service.
"""

from django.urls import path
from . import views

app_name = 'aiengine'

urlpatterns = [
    path('webhook/', views.EvolutionWebhookView.as_view(), name='evolution_webhook'),
    path('agent/', views.agent_detail, name='agent_detail'),
    path('agent/edit/', views.agent_edit, name='agent_edit'),
]
