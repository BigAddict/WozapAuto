from django.contrib import admin
from .models import KnowledgeBase


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
