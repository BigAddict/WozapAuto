from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField
import uuid


class KnowledgeBaseSettings(models.Model):
    """User-specific settings for knowledge base operations."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='knowledge_base_settings')
    
    # Embedding configuration
    embedding_dimensions = models.IntegerField(
        default=3072,
        help_text="Embedding vector dimensions. Gemini supports 128-3072. Higher = better quality but more storage. Recommended: 768, 1536, or 3072"
    )
    
    # Retrieval configuration
    similarity_threshold = models.FloatField(
        default=0.5,
        help_text="Minimum similarity score (0.0-1.0) for retrieval. Lower = more results but less precise. Recommended: 0.5-0.7"
    )
    top_k_results = models.IntegerField(
        default=5,
        help_text="Number of top similar chunks to retrieve from database"
    )
    max_chunks_in_context = models.IntegerField(
        default=3,
        help_text="Maximum number of knowledge base chunks to include in AI context"
    )
    
    # Chunking configuration
    chunk_size = models.IntegerField(
        default=1000,
        help_text="Number of characters per document chunk. Larger = more context but less precise retrieval"
    )
    chunk_overlap = models.IntegerField(
        default=200,
        help_text="Character overlap between chunks to preserve context across boundaries"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Knowledge Base Settings'
        verbose_name_plural = 'Knowledge Base Settings'
    
    def __str__(self):
        return f"Settings for {self.user.username}"
    
    def clean(self):
        """Validate settings values."""
        from django.core.exceptions import ValidationError
        
        if not (128 <= self.embedding_dimensions <= 3072):
            raise ValidationError("Embedding dimensions must be between 128 and 3072")
        
        if not (0.0 <= self.similarity_threshold <= 1.0):
            raise ValidationError("Similarity threshold must be between 0.0 and 1.0")
        
        if self.chunk_size <= 0:
            raise ValidationError("Chunk size must be positive")
        
        if self.chunk_overlap < 0:
            raise ValidationError("Chunk overlap cannot be negative")
        
        if self.chunk_overlap >= self.chunk_size:
            raise ValidationError("Chunk overlap must be less than chunk size")


class KnowledgeBase(models.Model):
    """Model to store knowledge base documents and their embeddings"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='knowledge_bases')
    original_filename = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='knowledge_base/%Y/%m/')
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=50, default='pdf')
    
    # Chunking metadata
    chunk_text = models.TextField()
    chunk_index = models.IntegerField(default=0)
    parent_document_id = models.CharField(max_length=255, db_index=True)
    
    # Vector embedding (Google Gemini: 3072 dimensions for better quality)
    embedding = VectorField(dimensions=3072)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    page_number = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'parent_document_id']),
            models.Index(fields=['parent_document_id', 'chunk_index']),
        ]
        verbose_name = 'Knowledge Base Entry'
        verbose_name_plural = 'Knowledge Base Entries'
    
    def __str__(self):
        return f"{self.original_filename} - Chunk {self.chunk_index}"
