from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from pydantic import BaseModel, Field
from pgvector.django import VectorField
from typing import Optional

class Agent(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_agents')
    name = models.CharField(max_length=255, default="WozapAutoAgent", unique=True, null=False, blank=False)
    description = models.TextField(default="WozapAutoAgent is a smart AI agent that will help you answer your WhatsApp queries.", null=False, blank=False)
    system_prompt = models.TextField(null=False, blank=False)
    is_active = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_locked_until = models.DateTimeField(null=True, blank=True)
    is_locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='locked_agents')
    locked_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class KnowledgeBase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='knowledge_bases')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    embedding = VectorField(dimensions=1536)
    metadata = models.JSONField(blank=True, null=True)
    # File metadata
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True)
    file_type = models.CharField(max_length=50, default='pdf')
    chunk_index = models.IntegerField(default=0)  # For tracking multiple chunks from same file
    parent_file_id = models.CharField(max_length=255, blank=True, null=True)  # Links chunks from same file
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Knowledge Base Entry'
        verbose_name_plural = 'Knowledge Base Entries'

    def __str__(self):
        return f"{self.name} - {self.user.username}"

class WebhookData(models.Model):
    message_id = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event = models.CharField(max_length=255)
    instance = models.CharField(max_length=255)
    remote_jid = models.CharField(max_length=255)
    from_me = models.BooleanField()
    push_name = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    conversation = models.CharField(max_length=255)
    message_type = models.CharField(max_length=255)
    instance_id = models.CharField(max_length=255)
    date_time = models.DateTimeField()
    sender = models.CharField(max_length=255)
    quoted_message = models.JSONField()
    is_group = models.BooleanField()
    is_processed = models.BooleanField(default=False)
    response_text = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-date_time']
        verbose_name = 'Webhook Data'
        verbose_name_plural = 'Webhook Data'

    def __str__(self):
        return f"{self.message_id} - {self.date_time}"

class EvolutionWebhookData(BaseModel):
    message_id: str
    event: str
    instance: str
    remote_jid: str
    from_me: bool
    push_name: str
    status: str
    conversation: str
    message_type: str
    instance_id: str
    date_time: datetime
    sender: str
    quoted_message: dict
    is_group: bool

class DocumentMetadata(BaseModel):
    name: str
    description: str
    metadata: dict

class AgentResponse(BaseModel):
    reply_needed: bool = Field(description="Whether the agent needs to reply to the user.")
    reply_text: Optional[str] = Field(description="The text of the reply to the user.")

class DocumentRelationship(models.Model):
    RELATIONSHIP_TYPES = [
        ('LINK', 'Explicit Link'),
        ('SIMILAR', 'Vector Similarity'),
        ('REFERENCE', 'Content Reference'),
        ('TAG', 'Shared Tag'),
    ]
    
    source = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='outgoing_links')
    target = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='incoming_links')
    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_TYPES)
    strength = models.FloatField(default=1.0)  # For similarity-based edges
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['source', 'target', 'relationship_type']
        verbose_name = 'Document Relationship'
        verbose_name_plural = 'Document Relationships'

    def __str__(self):
        return f"{self.source.name} -> {self.target.name} ({self.relationship_type})"

class DocumentTag(models.Model):
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['knowledge_base', 'name']
        verbose_name = 'Document Tag'
        verbose_name_plural = 'Document Tags'

    def __str__(self):
        return f"{self.name} - {self.knowledge_base.name}"