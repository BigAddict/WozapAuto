"""
URL configuration for knowledgebase app.
"""
from django.urls import path
from . import views

app_name = 'knowledgebase'

urlpatterns = [
    # Main knowledge base views
    path('', views.knowledge_base_list, name='knowledge_base_list'),
    path('upload/', views.knowledge_base_upload, name='knowledge_base_upload'),
    path('search/', views.knowledge_base_search, name='knowledge_base_search'),
    path('delete/<str:document_id>/', views.knowledge_base_delete, name='knowledge_base_delete'),
    path('document/<str:document_id>/', views.knowledge_base_document_detail, name='knowledge_base_document_detail'),
    
    # API endpoints
    path('api/', views.KnowledgeBaseAPIView.as_view(), name='knowledge_base_api'),
]
