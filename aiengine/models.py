from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from pydantic import BaseModel, Field
from pgvector.django import VectorField
from typing import Optional

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

    def __str__(self):
        return self.name

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