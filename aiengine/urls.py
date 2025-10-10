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
    path('webhook/', views.EvolutionWebhookView.as_view(), name='evolution_webhook'),
    path('', views.AgentDetailsView.as_view(), name='agent_details'),
    # Agent management
    path('agent/toggle-status/', views.ToggleAgentStatusView.as_view(), name='toggle_agent_status'),
    path('agent/edit/', views.AgentEditView.as_view(), name='edit_agent'),
    # Knowledge base management
    path('knowledge-base/', views.KnowledgeBaseManagementView.as_view(), name='knowledge_base_management'),
    path('retrieve-knowledge/', views.retrieve_knowledge_view, name='retrieve_knowledge'),
    # Knowledge graph
    path('graph/', views.GraphExplorerView.as_view(), name='knowledge-graph'),
    path('graph/data/', views.KnowledgeGraphView.as_view(), name='knowledge-graph-data'),
]
