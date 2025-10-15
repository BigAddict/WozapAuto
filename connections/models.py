from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from pydantic import BaseModel
from django.db import models
from enum import Enum
from typing import Optional
from django.dispatch import receiver
from django.db.models.signals import post_save

from aiengine.models import Agent

UserModel = get_user_model()

class ConnectionState(models.TextChoices):
    OPEN = "open"
    CONNECTING = "connecting"
    DISCONNECTED = "close"

class Connection(models.Model):
    instance_id = models.CharField(_("Instance ID"), max_length=255, unique=True)
    instance_name = models.CharField(_("Instance Name"), max_length=255)
    ownerPhone = models.CharField(_("Owner Phone"), max_length=255)
    profileName = models.CharField(_("Profile Name"), max_length=255)
    connection_status = models.CharField(_("Connection Status"), max_length=255, choices=ConnectionState.choices)
    instance_api_key = models.CharField(_("Instance API Key"), max_length=255)
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    # Retry tracking fields for new connection flow
    retry_count = models.IntegerField(_("Retry Count"), default=0, help_text="Number of retry attempts")
    last_retry_at = models.DateTimeField(_("Last Retry At"), null=True, blank=True, help_text="Last retry attempt timestamp")
    connection_attempts = models.IntegerField(_("Connection Attempts"), default=0, help_text="Total connection attempts")
    max_retries_reached = models.BooleanField(_("Max Retries Reached"), default=False, help_text="Whether max retries have been reached")
    connection_phase = models.CharField(
        _("Connection Phase"), 
        max_length=20, 
        default='initial',
        choices=[
            ('initial', 'Initial'),
            ('waiting', 'Waiting for Connection'),
            ('retrying', 'Retrying'),
            ('connected', 'Connected'),
            ('failed', 'Failed'),
            ('help_needed', 'Help Needed')
        ],
        help_text="Current phase of the connection process"
    )
    
    # QR code request tracking fields
    qr_code_requests = models.IntegerField(_("QR Code Requests"), default=0, help_text="Number of QR code requests")
    last_qr_request_at = models.DateTimeField(_("Last QR Request At"), null=True, blank=True, help_text="Last QR code request timestamp")
    max_qr_requests_reached = models.BooleanField(_("Max QR Requests Reached"), default=False, help_text="Whether max QR code requests have been reached")

    class Meta:
        verbose_name = _("Connection")
        verbose_name_plural = _("Connections")

    def __str__(self):
        return f"{self.instance_name} for {self.user.username}"
    
    def can_retry(self):
        """Check if connection can be retried (not at max retries and not in cooldown)"""
        if self.max_retries_reached:
            if self.last_retry_at:
                from django.utils import timezone
                time_diff = timezone.now() - self.last_retry_at
                # Check if 2 hours (7200 seconds) have passed
                return time_diff.total_seconds() >= 7200
            return False
        return True
    
    def increment_retry(self):
        """Increment retry count and update timestamps"""
        from django.utils import timezone
        self.retry_count += 1
        self.connection_attempts += 1
        self.last_retry_at = timezone.now()
        
        # Check if max retries reached
        if self.retry_count >= 5:
            self.max_retries_reached = True
            self.connection_phase = 'help_needed'
        else:
            self.connection_phase = 'retrying'
        
        self.save()
    
    def reset_retry_status(self):
        """Reset retry status when cooldown period is over"""
        self.retry_count = 0
        self.max_retries_reached = False
        self.connection_phase = 'initial'
        self.save()
    
    def is_connected(self):
        """Check if connection is in open/connected state"""
        return self.connection_status == 'open'
    
    def is_connecting(self):
        """Check if connection is in connecting state"""
        return self.connection_status in ['connecting', 'close']
    
    def can_request_qr_code(self):
        """Check if user can request a new QR code (not at max requests and not in cooldown)"""
        if self.max_qr_requests_reached:
            if self.last_qr_request_at:
                from django.utils import timezone
                time_diff = timezone.now() - self.last_qr_request_at
                # Check if 2 hours (7200 seconds) have passed
                return time_diff.total_seconds() >= 7200
            return False
        return True
    
    def increment_qr_request(self):
        """Increment QR code request count and update timestamps"""
        from django.utils import timezone
        self.qr_code_requests += 1
        self.last_qr_request_at = timezone.now()
        
        # Check if max QR requests reached
        if self.qr_code_requests >= 5:
            self.max_qr_requests_reached = True
        
        self.save()
    
    def reset_qr_request_status(self):
        """Reset QR code request status when cooldown period is over"""
        self.qr_code_requests = 0
        self.max_qr_requests_reached = False
        self.save()

@receiver(post_save, sender=Connection)
def create_agent_for_connection(sender, instance, created, **kwargs):
    """
    Automatically create an Agent for the same user when a Connection is created.
    The agent is inactive by default.
    """
    if created:
        # The agent name is unique, so use Connection instance_name plus user to avoid collision if needed
        agent_name = f"{instance.instance_name} Agent"
        Agent.objects.create(
            user=instance.user,
            name=agent_name,
            description="WozapAutoAgent is a smart AI agent that will help you answer your WhatsApp queries.",
            system_prompt="You are a smart AI agent that helps answer WhatsApp queries with accuracy and helpfulness.",
            is_active=False,
            is_locked=False,
        )

class EvolutionInstanceSettings(BaseModel):
    setting_id: str
    reject_calls: bool
    msg_call: str
    groups_ignore: bool
    always_online: bool
    read_messages: bool
    read_status: bool

class EvolutionInstanceCount(BaseModel):
    messages: int
    contacts: int
    chat: int

class EvolutionConnectionState(BaseModel):
    instance_name: str
    state: ConnectionState

class EvolutionInstance(BaseModel):
    instance_id: str
    instance_name: str
    connection_status: ConnectionState
    owner_jid: Optional[str] = None
    profile_name: Optional[str] = None
    profile_pic_url: Optional[str] = None
    integration: str
    phone_number: str
    api_token: str
    disconnection_object: Optional[str] = None
    created_at: str
    updated_at: str
    settings: EvolutionInstanceSettings
    count: EvolutionInstanceCount

class EvolutionInstanceCreate(BaseModel):
    instance_name: str
    connect_now: bool # qrcode field in evolution api
    phone_number: str  # Phone number WITHOUT + sign (e.g., "254799389806" not "+254799389806")

class EvolutionInstanceData(BaseModel):
    instance_name: str
    instance_id: str
    integration: str
    webhook_wa_business: Optional[str] = None
    access_token_wa_business: str = ""
    status: str  # Will be validated against ConnectionState values

class EvolutionQRCodeData(BaseModel):
    pairing_code: Optional[str] = None
    code: str
    base64: str
    count: int

class EvolutionInstanceDisconnectResponse(BaseModel):
    status: str
    error: bool
    message: str

class EvolutionInstanceCreateResponse(BaseModel):
    instance: EvolutionInstanceData
    hash: str
    webhook: dict = {}
    websocket: dict = {}
    rabbitmq: dict = {}
    nats: dict = {}
    sqs: dict = {}
    settings: EvolutionInstanceSettings
    qrcode: EvolutionQRCodeData = None