from django.contrib import admin

from .models import WebhookData, Agent

admin.site.register(WebhookData)
admin.site.register(Agent)