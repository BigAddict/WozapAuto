from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime, timezone
from aiengine.models import EvolutionWebhookData, WebhookData, Agent
from django.views import View
import logging
import json
from typing import Optional
from django.contrib.auth.models import User

from aiengine.service import ChatAssistant
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from .forms import AgentEditForm

logger = logging.getLogger("aiengine.views")

@method_decorator(csrf_exempt, name='dispatch')
class EvolutionWebhookView(View):
    """
    Class based webhook endpoint for receiving messages from Evolution API.
    """

    def post(self, request: HttpRequest):
        try:
            data = json.loads(request.body.decode('utf-8'))
            if not data and not data.get('event', ''):
                logger.warning("No data or event in webhook request. Skipping...")
                return JsonResponse({'success': True})

            # Enforce tenant identity via webhook query param: user_id
            user_id_param = request.GET.get('user_id', '').strip()
            if not user_id_param:
                logger.warning("Missing user_id in webhook URL. Skipping...")
                return JsonResponse({'success': False, 'error': 'Missing user_id in webhook URL'}, status=400)

            payload = data.get('data', {})
            key = payload.get('key', {})
            context_info = payload.get('contextInfo', {})
            quoted_message = context_info.get('quotedMessage', {})

            date_time_val = payload.get('messageTimestamp')

            try:
                date_time_ext = datetime.fromtimestamp(date_time_val, tz=timezone.utc) if date_time_val else None
                logger.info(f"Date time extracted from webhook: {date_time_ext}")
            except Exception:
                date_time_ext = datetime.now(timezone.utc)
                logger.info(f"Date time extracted from webhook: {date_time_ext}")

            remote_jid = key.get('remoteJid', '')
            is_group = remote_jid.endswith('@g.us')

            evolution_webhook_data = EvolutionWebhookData(
                message_id=key.get('id', payload.get('id', '')),
                event=data.get('event', ''),
                instance=data.get('instance', ''),
                remote_jid=remote_jid,
                from_me=key.get('fromMe', False),
                push_name=payload.get('pushName', ''),
                status=payload.get('status', ''),
                conversation=payload.get('message', {}).get('conversation', ''),
                message_type=payload.get('messageType', ''),
                instance_id=payload.get('instanceId', ''),
                date_time=date_time_ext,
                sender=data.get('sender', ''),
                quoted_message=quoted_message,
                is_group=is_group
            )
            # Validate that instance belongs to user_id from query (if possible)
            try:
                from connections.models import Connection
                conn = Connection.objects.filter(instance_id=evolution_webhook_data.instance_id).first()
                if not conn or str(conn.user_id) != user_id_param:
                    logger.warning("Webhook user_id mismatch or unknown instance. Skipping...")
                    return JsonResponse({'success': False, 'error': 'Webhook user_id mismatch or unknown instance'}, status=403)
                logger.info(f"Webhook user_id matched with instance: {conn.instance_name}")
            except Exception:
                # If validation cannot be performed, still proceed but log
                logger.warning('Could not validate webhook instance ownership for user_id=%s', user_id_param)

            # Processing goes here
            self.process_webhook(evolution_webhook_data)
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def process_webhook(self, data: EvolutionWebhookData) -> bool:
        try:
            self.save_to_db(data)
            if data.from_me:
                self.update_db_with_response(data, "Message from me")
                logger.info(f"Webhook is a message from me: {data.message_id}. Skipping...")
                return True

            if data.is_group:
                self.update_db_with_response(data, "Message from a group")
                logger.info(f"Webhook is a message from a group: {data.message_id}. Skipping...")
                return True

            user_agent = self._get_user_agent(user_id=self._get_user_from_instance_id(data.instance_id).id)
            if not user_agent:
                logger.error(f"User agent not found for user id: {self._get_user_from_instance_id(data.instance_id).id}")
                return False
            print(user_agent)
            
            from connections.services import evolution_api_service
            chat_assistant = ChatAssistant(f"{data.sender}x{data.remote_jid}", user_agent.system_prompt)
            response = chat_assistant.send_message(data.conversation)
            self.update_db_with_response(data, response.content)

            success, _ = evolution_api_service.send_text_message(
                instance_name=data.instance,
                number=data.remote_jid,
                message=response.content,
                reply_to_message_id=data.message_id
            )
            if not success:
                logger.error(f"Failed to send message to {data.remote_jid}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False

    def save_to_db(self, data: EvolutionWebhookData) -> bool:
        try:
            webhook_data = WebhookData.objects.create(
                message_id=data.message_id,
                user=self._get_user_from_instance_id(data.instance_id),
                event=data.event,
                instance=data.instance,
                remote_jid=data.remote_jid,
                from_me=data.from_me,
                push_name=data.push_name,
                status=data.status,
                conversation=data.conversation,
                message_type=data.message_type,
                instance_id=data.instance_id,
                date_time=data.date_time,
                sender=data.sender,
                quoted_message=data.quoted_message,
                is_group=data.is_group
            )
            webhook_data.save()
            logger.info(f"Webhook data saved to database: {webhook_data.message_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving webhook data to database: {e}")
            return False

    def update_db_with_response(self, data: EvolutionWebhookData, response: str) -> bool:
        try:
            webhook_data = WebhookData.objects.get(message_id=data.message_id)
            webhook_data.response_text = response
            webhook_data.is_processed = True
            webhook_data.save()
            logger.info(f"Webhook{webhook_data.message_id} updated")
            return True
        except Exception as e:
            logger.error(f"Error updating webhook data with response: {e}")
            return False

    def _get_user_from_instance_id(self, instance_id: str) -> Optional[User]:
        try:
            from connections.models import Connection
            connection = Connection.objects.get(instance_id=instance_id)
            return connection.user
        except Exception as e:
            logger.error(f"Error getting user from instance id: {e}")
            return None

    def _get_user_agent(self, user_id: str) -> Optional[Agent]:
        try:
            # Get the first active agent for the user, or the first one if none are active
            agent = Agent.objects.filter(user_id=user_id).order_by('-is_active', 'created_at').first()
            return agent
        except Exception as e:
            logger.error(f"Error getting user agent: {e}")
            return None


@login_required
def agent_detail(request: HttpRequest):
    try:
        # Get the user's primary agent (active first, then by creation date)
        agent = Agent.objects.filter(user=request.user).order_by('-is_active', 'created_at').first()
        
        # If no agent exists, create one
        if not agent:
            agent = Agent.objects.create(
                user=request.user,
                name='WozapAutoAgent',
                description='WozapAutoAgent is a smart AI agent that will help you answer your WhatsApp queries.',
                system_prompt='You are WozapAuto, a helpful WhatsApp assistant for the user. Be concise, friendly, and actionable. Always consider user context.',
                is_active=True
            )
    except Exception:
        messages.error(request, 'Unable to load your agent. Please try again later.')
        return redirect('core:dashboard') if 'core:dashboard' else redirect('/')

    return render(request, 'aiengine/agent_detail.html', {
        'agent': agent
    })


@login_required
def agent_edit(request: HttpRequest):
    try:
        # Get the user's primary agent (active first, then by creation date)
        agent = Agent.objects.filter(user=request.user).order_by('-is_active', 'created_at').first()
        
        # If no agent exists, create one
        if not agent:
            agent = Agent.objects.create(
                user=request.user,
                name='WozapAutoAgent',
                description='WozapAutoAgent is a smart AI agent that will help you answer your WhatsApp queries.',
                system_prompt='You are WozapAuto, a helpful WhatsApp assistant for the user. Be concise, friendly, and actionable. Always consider user context.',
                is_active=True
            )
    except Exception:
        messages.error(request, 'Unable to load your agent. Please try again later.')
        return redirect('aiengine:agent_detail')

    if request.method == 'POST':
        form = AgentEditForm(request.POST, initial={
            'description': agent.description,
            'system_prompt': agent.system_prompt
        })
        if form.is_valid():
            agent.description = form.cleaned_data['description']
            agent.system_prompt = form.cleaned_data['system_prompt']
            agent.save()
            messages.success(request, 'Agent updated successfully.')
            return redirect(reverse('aiengine:agent_detail'))
    else:
        form = AgentEditForm(initial={
            'description': agent.description,
            'system_prompt': agent.system_prompt
        })

    return render(request, 'aiengine/agent_edit.html', {
        'form': form,
        'agent': agent
    })