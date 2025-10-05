from django.contrib import admin

from .models import WebhookData, Agent, KnowledgeBase

admin.site.register(WebhookData)
admin.site.register(Agent)
admin.site.register(KnowledgeBase)