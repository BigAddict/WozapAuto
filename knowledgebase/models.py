from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField
import uuid


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
    
    # Vector embedding (Google Gemini: 768 dimensions - recommended for efficiency)
    embedding = VectorField(dimensions=768)
    
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
