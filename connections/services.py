from typing import Optional, Tuple, Union
import requests

from base.env_config import EVOLUTION_API_KEY, EVOLUTION_HOST_URL
from .models import (
    EvolutionInstance,
    EvolutionInstanceSettings,
    EvolutionInstanceCount,
    EvolutionConnectionState,
    ConnectionState,
    EvolutionInstanceCreate,
    EvolutionInstanceCreateResponse,
    EvolutionInstanceData,
    EvolutionQRCodeData
)

class EvolutionAPIService:
    def __init__(self) -> None:
        self.admin_api_key = EVOLUTION_API_KEY
        self.host_url = EVOLUTION_HOST_URL

    def get_headers(self, api_key: Optional[str] = None) -> dict:
        if api_key is None:
            api_key = self.admin_api_key
        return {
            'apikey': api_key,
            'Content-Type': 'application/json',
        }

    def create_instance(self, instance_create: EvolutionInstanceCreate) -> Tuple[bool, Union[EvolutionInstanceCreateResponse, str]]:
        """
        Create a new Evolution API instance.
        
        Returns:
            Tuple[bool, Union[EvolutionInstanceCreateResponse, str]]: 
            - (True, EvolutionInstanceCreateResponse) on success
            - (False, error_message) on failure
        """
        try:
            url = f"{self.host_url}/instance/create"
            headers = self.get_headers()
            payload = {
                "instanceName": instance_create.instance_name,
                "qrcode": instance_create.connect_now,
                "number": instance_create.phone_number,
                "integration": "WHATSAPP-BAILEYS",
                "rejectCall": True,
                "alwaysOnline": True,
                "readMessages": True,
                "readStatus": False,
                "syncFullHistory": False,
                "webhook": {
                    "url": "https://n8n.bigaddict.shop/webhook/wozapauto/ai",
                    "byEvents": False,
                    "base64": False,
                    "events": ["MESSAGES_UPSERT"]
                }
            }
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the response data
            instance_data = data.get('instance', {})
            settings_data = data.get('settings', {})
            qrcode_data = data.get('qrcode', {})
            
            # Create settings object
            settings = EvolutionInstanceSettings(
                setting_id="",  # Not provided in create response
                reject_calls=settings_data.get('rejectCall', False),
                msg_call=settings_data.get('msgCall', ''),
                groups_ignore=settings_data.get('groupsIgnore', False),
                always_online=settings_data.get('alwaysOnline', False),
                read_messages=settings_data.get('readMessages', False),
                read_status=settings_data.get('readStatus', False)
            )
            
            # Create instance data object
            instance = EvolutionInstanceData(
                instance_name=instance_data.get('instanceName', ''),
                instance_id=instance_data.get('instanceId', ''),
                integration=instance_data.get('integration', ''),
                webhook_wa_business=instance_data.get('webhookWaBusiness'),
                access_token_wa_business=instance_data.get('accessTokenWaBusiness', ''),
                status=instance_data.get('status', '')
            )
            
            # Create QR code data object if present
            qrcode = None
            if qrcode_data:
                qrcode = EvolutionQRCodeData(
                    pairing_code=qrcode_data.get('pairingCode', ''),
                    code=qrcode_data.get('code', ''),
                    base64=qrcode_data.get('base64', ''),
                    count=qrcode_data.get('count', 0)
                )
            
            # Create the complete response object
            create_response = EvolutionInstanceCreateResponse(
                instance=instance,
                hash=data.get('hash', ''),
                webhook=data.get('webhook', {}),
                websocket=data.get('websocket', {}),
                rabbitmq=data.get('rabbitmq', {}),
                nats=data.get('nats', {}),
                sqs=data.get('sqs', {}),
                settings=settings,
                qrcode=qrcode
            )
            
            return True, create_response
            
        except requests.exceptions.Timeout:
            return False, "Request timeout - WhatsApp host is not responding"
        except requests.exceptions.ConnectionError:
            return False, "Connection error - Unable to reach WhatsApp host"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return False, "Invalid API key - Authentication failed"
            elif e.response.status_code == 409:
                return False, "Instance name already exists"
            else:
                return False, f"HTTP error {e.response.status_code}: {e.response.text}"
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def get_instance(self, instance_id: str) -> Tuple[bool, Union[EvolutionInstance, str]]:
        """
        Fetch instance data from Evolution API.
        
        Returns:
            Tuple[bool, Union[EvolutionInstance, str]]: 
            - (True, EvolutionInstance) on success
            - (False, error_message) on failure
        """
        try:
            url = f"{self.host_url}/instance/fetchInstances"
            headers = self.get_headers()
            params = {
                "instanceId": instance_id
            }
            response = requests.get(url, headers=headers, timeout=30, params=params)
            response.raise_for_status()
            
            # Parse the response data
            data = response.json()
            
            # Since the API returns an array with one item, get the first item
            if not data or len(data) == 0:
                return False, "No instance data found in response"
            
            instance_data = data[0]  # Get the first (and only) instance
            
            # Extract settings data
            settings_data = instance_data.get('Setting', {})
            settings = EvolutionInstanceSettings(
                setting_id=settings_data.get('id', ''),
                reject_calls=settings_data.get('rejectCall', False),
                msg_call=settings_data.get('msgCall', ''),
                groups_ignore=settings_data.get('groupsIgnore', False),
                always_online=settings_data.get('alwaysOnline', False),
                read_messages=settings_data.get('readMessages', False),
                read_status=settings_data.get('readStatus', False)
            )
            
            # Extract count data
            count_data = instance_data.get('_count', {})
            count = EvolutionInstanceCount(
                messages=count_data.get('Message', 0),
                contacts=count_data.get('Contact', 0),
                chat=count_data.get('Chat', 0)
            )
            
            # Create and return EvolutionInstance
            instance = EvolutionInstance(
                instance_id=instance_data.get('id', ''),
                instance_name=instance_data.get('name', ''),
                connection_status=instance_data.get('connectionStatus', ''),
                owner_jid=instance_data.get('ownerJid', ''),
                profile_name=instance_data.get('profileName', ''),
                profile_pic_url=instance_data.get('profilePicUrl', ''),
                intergration=instance_data.get('integration', ''),
                phone_number=instance_data.get('number', ''),
                api_token=instance_data.get('token', ''),
                disconnection_object=instance_data.get('disconnectionObject', ''),
                created_at=instance_data.get('createdAt', ''),
                updated_at=instance_data.get('updatedAt', ''),
                settings=settings,
                count=count
            )
            
            return True, instance
            
        except requests.exceptions.Timeout:
            return False, "Request timeout -whasapp host is not responding"
        except requests.exceptions.ConnectionError:
            return False, "Connection error - Unable to reach whasapp host"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"Invalid API key - Authentication failed : {e.response.text}")
                return False, "Invalid API key - Authentication failed"
            elif e.response.status_code == 404:
                return False, "Instance not found"
            else:
                return False, f"HTTP error {e.response.status_code}: {e.response.text}"
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def get_connection_state(self, instance_name: str) -> Tuple[bool, Union[EvolutionConnectionState, str]]:
        try:
            url = f"{self.host_url}/instance/connectionState/{instance_name}"
            headers = self.get_headers()
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return True, EvolutionConnectionState(
                instance_name=response.json().get('instanceName', ''),
                state=response.json().get('state', ConnectionState.DISCONNECTED)
            )
        except requests.exceptions.Timeout:
            return False, "Request timeout -whasapp host is not responding"
        except requests.exceptions.ConnectionError:
            return False, "Connection error - Unable to reach whasapp host"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return False, "Invalid API key - Authentication failed"
            elif e.response.status_code == 404:
                return False, "Instance not found"
            else:
                return False, f"HTTP error {e.response.status_code}: {e.response.text}"


evolution_api_service = EvolutionAPIService()