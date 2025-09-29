from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from pydantic import BaseModel
from django.db import models
from enum import Enum

UserModel = get_user_model()

class ConnectionState(models.TextChoices):
    OPEN = "open"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"

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

    class Meta:
        verbose_name = _("Connection")
        verbose_name_plural = _("Connections")

    def __str__(self):
        return f"{self.instance_name} for {self.user.username}"

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
    owner_jid: str
    profile_name: str
    profile_pic_url: str
    intergration: str
    phone_number: str
    api_token: str
    disconnection_object: str
    created_at: str
    updated_at: str
    settings: EvolutionInstanceSettings
    count: EvolutionInstanceCount

class EvolutionInstanceCreate(BaseModel):
    instance_name: str
    connect_now: bool # qrcode field in evolution api
    phone_number: str

class EvolutionInstanceData(BaseModel):
    instance_name: str
    instance_id: str
    integration: str
    webhook_wa_business: str = None
    access_token_wa_business: str = ""
    status: ConnectionState

class EvolutionQRCodeData(BaseModel):
    pairing_code: str
    code: str
    base64: str
    count: int

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