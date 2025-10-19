from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
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
        'created_at', 'updated_at', 'embedding'
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': ('user', 'original_filename', 'file_path', 'file_size', 'file_type')
        }),
        ('Chunk Information', {
            'fields': ('parent_document_id', 'chunk_index', 'chunk_text', 'page_number')
        }),
        ('Embedding & Metadata', {
            'fields': ('embedding', 'metadata'),
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
