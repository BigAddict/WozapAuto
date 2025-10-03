from django.db import models
from django.contrib.auth.models import User

# class Agent(models.Model):
#     name = models.CharField(max_length=255, default="WozapAutoAgent", unique=True, null=False, blank=False)
#     description = models.TextField(default="WozapAutoAgent is a smart AI agent that will help you answer your WhatsApp queries.", null=False, blank=False)
#     prompt = models.TextField(null=False, blank=False)
#     system_prompt = models.TextField(null=False, blank=False)
#     is_active = models.BooleanField(default=True)
#     is_locked = models.BooleanField(default=False)
#     is_locked_until = models.DateTimeField(null=True, blank=True)
#     is_locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
#     locked_reason = models.TextField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.name