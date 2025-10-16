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
    path('conversations/', views.conversation_history, name='conversation_history'),
    path('conversations/<str:thread_id>/', views.conversation_detail, name='conversation_detail'),
    path('memory/', views.memory_management, name='memory_management'),
    path('memory/cleanup/', views.cleanup_memory, name='cleanup_memory'),
    path('memory/search/', views.test_semantic_search, name='test_semantic_search'),
]
