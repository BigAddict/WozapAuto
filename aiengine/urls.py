"""
URL configuration for the AI Engine application.

This module defines the URL patterns for testing and interacting with the WhatsApp AI agent service.
"""

from django.urls import path
from . import views

app_name = 'aiengine'

urlpatterns = [
    path('webhook/', views.EvolutionWebhookView.as_view(), name='evolution_webhook'),
    path('agent/', views.AgentDetailView.as_view(), name='agent_detail'),
    path('agent/edit/', views.agent_edit, name='agent_edit'),
    path('conversations/', views.ConversationHistoryView.as_view(), name='conversation_history'),
    path('conversations/<str:thread_id>/', views.ConversationDetailView.as_view(), name='conversation_detail'),
    path('conversations/<str:thread_id>/delete/', views.delete_conversation_thread, name='delete_conversation_thread'),
    path('conversations/<str:thread_id>/clear/', views.clear_conversation_messages, name='clear_conversation_messages'),
    path('conversations/delete-all/all/', views.delete_all_conversations, name='delete_all_conversations'),
    path('memory/', views.MemoryManagementView.as_view(), name='memory_management'),
    path('memory/cleanup/', views.cleanup_memory, name='cleanup_memory'),
    path('memory/search/', views.test_semantic_search, name='test_semantic_search'),
    path('webhook/reengage/', views.reengage_webhook, name='reengage_webhook'),
    
    # Token usage dashboard (admin only)
    path('tokens/', views.TokenDashboardView.as_view(), name='token_dashboard'),
    path('tokens/user/<int:user_id>/', views.UserTokenDetailsView.as_view(), name='user_token_details'),
    path('tokens/export/', views.token_export, name='token_export'),
]
