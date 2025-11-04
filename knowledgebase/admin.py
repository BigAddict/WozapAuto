from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
import numpy as np
from .models import KnowledgeBase, KnowledgeBaseSettings
from .service import KnowledgeBaseService


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    """Admin interface for KnowledgeBase model."""
    
    list_display = [
        'original_filename', 'user', 'parent_document_id', 'chunk_index', 
        'file_size', 'created_at'
    ]
    
    list_filter = [
        'user', 'file_type', 'created_at', 'parent_document_id'
    ]
    
    search_fields = [
        'original_filename', 'chunk_text', 'parent_document_id'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at', 'embedding_display'
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': ('user', 'original_filename', 'file_path', 'file_size', 'file_type')
        }),
        ('Chunk Information', {
            'fields': ('parent_document_id', 'chunk_index', 'chunk_text', 'page_number')
        }),
        ('Embedding & Metadata', {
            'fields': ('embedding_display', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related('user')
    
    def chunk_text_preview(self, obj):
        """Show a preview of the chunk text."""
        return obj.chunk_text[:100] + '...' if len(obj.chunk_text) > 100 else obj.chunk_text
    chunk_text_preview.short_description = 'Chunk Preview'
    
    def embedding_display(self, obj):
        """Display embedding vector in a safe format for admin."""
        if obj.embedding is None:
            return format_html('<span style="color: #999;">No embedding</span>')
        
        try:
            # Convert to numpy array if it isn't already
            if hasattr(obj.embedding, '__array__'):
                embedding_array = np.array(obj.embedding)
            else:
                embedding_array = obj.embedding
            
            # Get shape and first few values for display
            shape = embedding_array.shape if hasattr(embedding_array, 'shape') else (len(embedding_array),)
            first_values = embedding_array[:5] if len(embedding_array) >= 5 else embedding_array
            
            # Format display
            first_values_str = ', '.join([f'{val:.4f}' for val in first_values])
            return format_html(
                '<div style="font-family: monospace; font-size: 11px;">'
                '<strong>Shape:</strong> {}<br>'
                '<strong>First 5 values:</strong> [{}]<br>'
                '<strong>Min:</strong> {:.4f}, <strong>Max:</strong> {:.4f}, '
                '<strong>Mean:</strong> {:.4f}'
                '</div>',
                shape,
                first_values_str,
                float(np.min(embedding_array)) if hasattr(embedding_array, '__len__') and len(embedding_array) > 0 else 0,
                float(np.max(embedding_array)) if hasattr(embedding_array, '__len__') and len(embedding_array) > 0 else 0,
                float(np.mean(embedding_array)) if hasattr(embedding_array, '__len__') and len(embedding_array) > 0 else 0,
            )
        except (TypeError, AttributeError, ValueError) as e:
            return format_html('<span style="color: #dc3545;">Error displaying embedding: {}</span>', str(e))
    
    embedding_display.short_description = 'Embedding Vector'
    
    def has_add_permission(self, request):
        """Disable adding through admin - use the upload interface instead."""
        return False
    
    actions = ['regenerate_embeddings_for_documents']
    
    def regenerate_embeddings_for_documents(self, request, queryset):
        """Regenerate embeddings for selected documents."""
        if queryset.count() == 0:
            self.message_user(request, "No documents selected.", level=messages.WARNING)
            return
        
        # Group by parent_document_id
        document_ids = set(queryset.values_list('parent_document_id', flat=True))
        
        message = f"To regenerate embeddings for {len(document_ids)} documents, run: python manage.py regenerate_embeddings --document-id {' '.join(document_ids)}"
        
        self.message_user(
            request, 
            message, 
            level=messages.INFO
        )
    
    regenerate_embeddings_for_documents.short_description = "Regenerate embeddings for selected documents"


@admin.register(KnowledgeBaseSettings)
class KnowledgeBaseSettingsAdmin(admin.ModelAdmin):
    """Admin interface for KnowledgeBaseSettings model."""
    
    list_display = [
        'user', 'embedding_dimensions', 'similarity_threshold', 
        'chunk_size', 'chunk_overlap', 'max_chunks_in_context', 'updated_at'
    ]
    
    list_filter = [
        'embedding_dimensions', 'similarity_threshold', 'created_at', 'updated_at'
    ]
    
    search_fields = [
        'user__username', 'user__email'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at', 'embedding_stats'
    ]
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Embedding Configuration', {
            'fields': ('embedding_dimensions',),
            'description': 'Configure embedding vector dimensions. Higher dimensions provide better quality but use more storage.'
        }),
        ('Retrieval Configuration', {
            'fields': ('similarity_threshold', 'top_k_results', 'max_chunks_in_context'),
            'description': 'Configure how knowledge base search and retrieval works.'
        }),
        ('Chunking Configuration', {
            'fields': ('chunk_size', 'chunk_overlap'),
            'description': 'Configure how documents are split into chunks for processing.'
        }),
        ('Statistics', {
            'fields': ('embedding_stats',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-updated_at']
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related('user')
    
    def embedding_stats(self, obj):
        """Show embedding statistics for the user."""
        if not obj.user:
            return "No user associated"
        
        total_chunks = KnowledgeBase.objects.filter(user=obj.user).count()
        chunks_with_embeddings = KnowledgeBase.objects.filter(
            user=obj.user, 
            embedding__isnull=False
        ).count()
        
        return f"Total chunks: {total_chunks}, With embeddings: {chunks_with_embeddings}"
    embedding_stats.short_description = 'Embedding Statistics'
    
    actions = ['regenerate_embeddings_for_users']
    
    def regenerate_embeddings_for_users(self, request, queryset):
        """Regenerate embeddings for selected users."""
        user_count = queryset.count()
        if user_count == 0:
            self.message_user(request, "No settings selected.", level=messages.WARNING)
            return
        
        # Redirect to management command or show instructions
        usernames = [settings.user.username for settings in queryset]
        message = f"To regenerate embeddings for {user_count} users, run: python manage.py regenerate_embeddings --user {' '.join(usernames)}"
        
        self.message_user(
            request, 
            message, 
            level=messages.INFO
        )
    
    regenerate_embeddings_for_users.short_description = "Regenerate embeddings for selected users"
