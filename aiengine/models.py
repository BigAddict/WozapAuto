from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from pydantic import BaseModel, Field
from pgvector.django import VectorField
from typing import Optional
import json

class Agent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='owned_agents')
    name = models.CharField(max_length=255, default="WozapAutoAgent", null=False, blank=False)
    description = models.TextField(default="WozapAutoAgent is a smart AI agent that will help you answer your WhatsApp queries.", null=False, blank=False)
    system_prompt = models.TextField(null=False, blank=False)
    is_active = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_locked_until = models.DateTimeField(null=True, blank=True)
    is_locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='locked_agents')
    locked_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(user__isnull=False),
                name='unique_agent_per_user'
            )
        ]

    def __str__(self):
        return self.name

class WebhookData(models.Model):
    message_id = models.CharField(max_length=255, unique=True)  # Added unique constraint
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
        indexes = [
            models.Index(fields=['message_id']),  # Add index for faster lookups
            models.Index(fields=['is_processed']),
        ]

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

class ConversationThread(models.Model):
    """Represents a conversation thread between a user and the agent"""
    thread_id = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_threads')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='conversation_threads')
    remote_jid = models.CharField(max_length=255, help_text="WhatsApp contact/group ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
        unique_together = ['user', 'remote_jid']
    
    def __str__(self):
        return f"Thread {self.thread_id} - {self.remote_jid}"

class ConversationMessage(models.Model):
    """Stores individual messages in a conversation with embeddings for semantic search"""
    MESSAGE_TYPES = [
        ('human', 'Human'),
        ('ai', 'AI'),
        ('system', 'System'),
    ]
    
    thread = models.ForeignKey(ConversationThread, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    embedding = VectorField(dimensions=384, null=True, blank=True)  # Using 384 dimensions for all-MiniLM-L6-v2
    metadata = models.JSONField(default=dict, blank=True)
    
    # Token usage tracking
    input_tokens = models.IntegerField(null=True, blank=True, help_text="Number of input tokens used")
    output_tokens = models.IntegerField(null=True, blank=True, help_text="Number of output tokens generated")
    total_tokens = models.IntegerField(null=True, blank=True, help_text="Total tokens used (input + output)")
    model_name = models.CharField(max_length=100, null=True, blank=True, help_text="Model used for this message")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thread', 'created_at']),
            models.Index(fields=['message_type']),
        ]
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."

class ConversationCheckpoint(models.Model):
    """Stores LangGraph checkpoints for conversation state management"""
    thread = models.ForeignKey(ConversationThread, on_delete=models.CASCADE, related_name='checkpoints')
    checkpoint_id = models.CharField(max_length=255, unique=True, db_index=True)
    checkpoint_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Checkpoint {self.checkpoint_id} for {self.thread.thread_id}"