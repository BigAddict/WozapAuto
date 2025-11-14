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
from aiengine.memory_utils import get_memory_statistics, get_user_conversation_summary, cleanup_old_conversations
from aiengine.token_utils import get_token_statistics, get_user_token_summary, get_top_token_users
from aiengine.models import ConversationThread, ConversationMessage
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from .forms import AgentEditForm
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from core.decorators import business_profile_required

logger = logging.getLogger("aiengine.views")

@method_decorator(csrf_exempt, name='dispatch')
class EvolutionWebhookView(View):
    """
    Class based webhook endpoint for receiving messages from Evolution API.
    """

    def post(self, request: HttpRequest):
        try:
            data = json.loads(request.body.decode('utf-8'))
            print(len(data.keys()))
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

            base64_file = ''
            mime_type = ''
            if payload.get('messageType') == 'imageMessage':
                base64_file = payload.get('message', {}).get('base64', '')
                if not base64_file:
                    logger.warning("No base64 file in webhook request. Skipping...")
                conversation = payload.get('message', {}).get('imageMessage', {}).get('caption', '')
                mime_type = payload.get('message', {}).get('imageMessage', {}).get('mimetype', '')
                logger.info(f"Base64 file: {base64_file[:100]}...")
                logger.info(f"Mime type: {mime_type}")
                if not conversation:
                    logger.warning("No caption in image message. Skipping...")
                    conversation = ""
            else:
                conversation = payload.get('message', {}).get('conversation', '')

            evolution_webhook_data = EvolutionWebhookData(
                message_id=key.get('id', payload.get('id', '')),
                event=data.get('event', ''),
                instance=data.get('instance', ''),
                remote_jid=remote_jid,
                from_me=key.get('fromMe', False),
                push_name=payload.get('pushName', ''),
                status=payload.get('status', ''),
                conversation=conversation,
                message_type=payload.get('messageType', ''),
                instance_id=payload.get('instanceId', ''),
                date_time=date_time_ext,
                sender=data.get('sender', ''),
                quoted_message=quoted_message,
                is_group=is_group,
                base64_file=base64_file,
                mime_type=mime_type
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
            # Check if this message was already processed
            existing_webhook = WebhookData.objects.filter(message_id=data.message_id).first()
            if existing_webhook and existing_webhook.is_processed:
                logger.info(f"Message {data.message_id} already processed. Skipping...")
                return True
            
            # Save to database (this will skip if already exists)
            was_new_message = self.save_to_db(data)
            
            # If this was not a new message, don't process it again
            if not was_new_message:
                logger.info(f"Message {data.message_id} already exists in database. Skipping processing...")
                return True
            
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
            # Get user from instance
            user = self._get_user_from_instance_id(data.instance_id)
            if not user:
                logger.error(f"User not found for instance: {data.instance_id}")
                return False
            
            # Create ChatAssistant with database-backed memory
            chat_assistant = ChatAssistant(
                thread_id=data.remote_jid,
                system_instructions=user_agent.system_prompt,
                user=user,
                agent=user_agent,
                remote_jid=data.remote_jid
            )
            if data.base64_file:
                response = chat_assistant.send_message(data.conversation, data.base64_file, data.mime_type)
            else:
                response = chat_assistant.send_message(data.conversation)
            needs_reply = getattr(response, 'needs_reply', True)
            response_text = getattr(response, 'response_text', response.content)

            # Update DB with structured result
            try:
                webhook_data = WebhookData.objects.filter(message_id=data.message_id).first()
                if webhook_data:
                    webhook_data.response_text = response_text
                    webhook_data.needs_reply = needs_reply
                    webhook_data.is_processed = True
                    from django.utils import timezone as _tz
                    if hasattr(webhook_data, 'last_processed_at'):
                        webhook_data.last_processed_at = _tz.now()
                    webhook_data.processing_attempts = getattr(webhook_data, 'processing_attempts', 0) + 1
                    webhook_data.processing_error = None
                    webhook_data.save()
            except Exception as e:
                logger.warning(f"Failed to update webhook structured fields: {e}")

            # Only send to WhatsApp if needs_reply
            if needs_reply:
                success, _ = evolution_api_service.send_text_message(
                    instance_name=data.instance,
                    number=data.remote_jid,
                    message=response_text,
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
            from django.db import transaction
            
            with transaction.atomic():
                # Use get_or_create to handle race conditions
                webhook_data, created = WebhookData.objects.get_or_create(
                    message_id=data.message_id,
                    defaults={
                        'user': self._get_user_from_instance_id(data.instance_id),
                        'event': data.event,
                        'instance': data.instance,
                        'remote_jid': data.remote_jid,
                        'from_me': data.from_me,
                        'push_name': data.push_name,
                        'status': data.status,
                        'conversation': data.conversation,
                        'message_type': data.message_type,
                        'instance_id': data.instance_id,
                        'date_time': data.date_time,
                        'sender': data.sender,
                        'quoted_message': data.quoted_message,
                        'is_group': data.is_group,
                        'base64_file': data.base64_file,
                        'mime_type': data.mime_type
                    }
                )
                
                if created:
                    logger.info(f"Webhook data saved to database: {webhook_data.message_id}")
                    return True
                else:
                    logger.info(f"Webhook data already exists for message_id: {data.message_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error saving webhook data to database: {e}")
            return False

    def update_db_with_response(self, data: EvolutionWebhookData, response: str) -> bool:
        try:
            # Get the first webhook data record for this message_id
            webhook_data = WebhookData.objects.filter(message_id=data.message_id).first()
            if webhook_data:
                webhook_data.response_text = response
                webhook_data.is_processed = True
                webhook_data.save()
                logger.info(f"Webhook{webhook_data.message_id} updated")
                return True
            else:
                logger.warning(f"No webhook data found for message_id: {data.message_id}")
                return False
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


@method_decorator(login_required, name='dispatch')
class AgentDetailView(TemplateView):
    template_name = 'aiengine/agent_detail.html'

    @method_decorator(business_profile_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args, **kwargs):
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
            
            # Get memory statistics for this user
            memory_stats = get_user_conversation_summary(request.user.id)
            
            # Get recent conversations
            recent_threads = ConversationThread.objects.filter(
                user=request.user
            ).order_by('-updated_at')[:5]
            
            # Get conversation statistics
            total_messages = ConversationMessage.objects.filter(
                thread__user=request.user
            ).count()
            
            # Get messages with embeddings
            messages_with_embeddings = ConversationMessage.objects.filter(
                thread__user=request.user,
                embedding__isnull=False
            ).count()
            
            # Calculate embedding coverage
            embedding_coverage = (messages_with_embeddings / total_messages * 100) if total_messages > 0 else 0
            
            context = self.get_context_data(**kwargs)
            context.update({
                'agent': agent,
                'memory_stats': memory_stats,
                'recent_threads': recent_threads,
                'total_messages': total_messages,
                'embedding_coverage': embedding_coverage,
            })
            return self.render_to_response(context)
        except Exception as e:
            logger.error(f"Error loading agent detail: {e}")
            messages.error(request, 'Unable to load your agent. Please try again later.')
            return redirect('core:dashboard') if 'core:dashboard' else redirect('/')


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


@method_decorator(login_required, name='dispatch')
class ConversationHistoryView(TemplateView):
    template_name = 'aiengine/conversation_history.html'

    def get(self, request: HttpRequest, *args, **kwargs):
        try:
            # Get all conversation threads for the user
            threads = ConversationThread.objects.filter(user=request.user).order_by('-updated_at')
            
            # Paginate threads
            paginator = Paginator(threads, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            # Get message counts for each thread
            for thread in page_obj:
                thread.message_count = ConversationMessage.objects.filter(thread=thread).count()
                thread.last_message = ConversationMessage.objects.filter(
                    thread=thread
                ).order_by('-created_at').first()
            
            context = self.get_context_data(**kwargs)
            context.update({
                'page_obj': page_obj,
            })
            return self.render_to_response(context)
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            messages.error(request, 'Unable to load conversation history.')
            return redirect('aiengine:agent_detail')


@method_decorator(login_required, name='dispatch')
class ConversationDetailView(TemplateView):
    template_name = 'aiengine/conversation_detail.html'

    def get(self, request: HttpRequest, *args, **kwargs):
        try:
            thread_id = kwargs.get('thread_id')
            thread = get_object_or_404(ConversationThread, thread_id=thread_id, user=request.user)
            
            # Get messages for this thread
            msgs = ConversationMessage.objects.filter(thread=thread).order_by('created_at')
            
            # Get webhook data for this thread and merge with messages
            webhook_messages = WebhookData.objects.filter(
                user=request.user,
                remote_jid=thread.remote_jid
            ).order_by('date_time')
            
            # Create a combined list of messages and webhook messages
            combined_messages = []
            
            # Add regular conversation messages
            for msg in msgs:
                combined_messages.append({
                    'type': 'conversation',
                    'message': msg,
                    'webhook_data': None,
                    'timestamp': msg.created_at
                })
            
            # Add webhook messages
            for webhook in webhook_messages:
                combined_messages.append({
                    'type': 'webhook',
                    'message': None,
                    'webhook_data': webhook,
                    'timestamp': webhook.date_time
                })
            
            # Sort by timestamp
            combined_messages.sort(key=lambda x: x['timestamp'])
            
            # Paginate combined messages
            paginator = Paginator(combined_messages, 20)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            # Get conversation summary
            from aiengine.memory_service import MemoryService
            memory_service = MemoryService(thread)
            summary = memory_service.get_conversation_summary()
            
            context = self.get_context_data(**kwargs)
            context.update({
                'thread': thread,
                'page_obj': page_obj,
                'summary': summary,
            })
            return self.render_to_response(context)
        except Exception as e:
            logger.error(f"Error loading conversation detail: {e}")
            messages.error(request, 'Unable to load conversation details.')
            return redirect('aiengine:conversation_history')


@login_required
@require_POST
def delete_conversation_thread(request: HttpRequest, thread_id: str):
    """Delete a specific conversation thread and all its messages."""
    try:
        thread = get_object_or_404(ConversationThread, thread_id=thread_id, user=request.user)
        
        # Count messages before deletion
        message_count = ConversationMessage.objects.filter(thread=thread).count()
        
        # Delete the thread (cascade will delete messages)
        remote_jid = thread.remote_jid
        thread.delete()
        
        logger.info(f"Deleted thread {thread_id} with {message_count} messages for user {request.user.username}")
        messages.success(request, f'Successfully deleted conversation with {remote_jid} ({message_count} messages)')
        
        return redirect('aiengine:conversation_history')
        
    except Exception as e:
        logger.error(f"Error deleting conversation thread {thread_id}: {e}")
        messages.error(request, f'Failed to delete conversation: {str(e)}')
        return redirect('aiengine:conversation_history')


@login_required
@require_POST
def clear_conversation_messages(request: HttpRequest, thread_id: str):
    """Clear messages from a conversation thread."""
    try:
        thread = get_object_or_404(ConversationThread, thread_id=thread_id, user=request.user)
        
        # Get keep_recent parameter (default: 0 means delete all)
        keep_recent = int(request.POST.get('keep_recent', 0))
        
        if keep_recent > 0:
            # Keep N most recent messages
            messages_query = ConversationMessage.objects.filter(thread=thread).order_by('-created_at')
            total_count = messages_query.count()
            
            if total_count <= keep_recent:
                messages.info(request, f'No messages to delete. Thread has {total_count} messages.')
                return redirect('aiengine:conversation_detail', thread_id=thread_id)
            
            # Get IDs of messages to keep
            keep_ids = list(messages_query[:keep_recent].values_list('id', flat=True))
            
            # Delete messages not in keep list
            deleted_count = ConversationMessage.objects.filter(thread=thread).exclude(id__in=keep_ids).delete()[0]
            
            messages.success(request, f'Cleared {deleted_count} messages (kept {keep_recent} most recent)')
        else:
            # Delete all messages
            deleted_count = ConversationMessage.objects.filter(thread=thread).delete()[0]
            messages.success(request, f'Cleared all {deleted_count} messages from conversation')
        
        logger.info(f"Cleared {deleted_count} messages from thread {thread_id} (kept {keep_recent}) for user {request.user.username}")
        
        return redirect('aiengine:conversation_detail', thread_id=thread_id)
        
    except Exception as e:
        logger.error(f"Error clearing messages from thread {thread_id}: {e}")
        messages.error(request, f'Failed to clear messages: {str(e)}')
        return redirect('aiengine:conversation_detail', thread_id=thread_id)


@login_required
@require_POST
def delete_all_conversations(request: HttpRequest):
    """Delete all conversation threads for the current user."""
    try:
        # Count threads and messages
        threads = ConversationThread.objects.filter(user=request.user)
        thread_count = threads.count()
        
        total_messages = 0
        for thread in threads:
            total_messages += ConversationMessage.objects.filter(thread=thread).count()
        
        # Delete all threads (cascade will delete messages)
        threads.delete()
        
        logger.info(f"Deleted all {thread_count} threads with {total_messages} messages for user {request.user.username}")
        messages.success(request, f'Successfully deleted all {thread_count} conversations ({total_messages} total messages)')
        
        return redirect('aiengine:conversation_history')
        
    except Exception as e:
        logger.error(f"Error deleting all conversations for user {request.user.username}: {e}")
        messages.error(request, f'Failed to delete conversations: {str(e)}')
        return redirect('aiengine:conversation_history')


@method_decorator(login_required, name='dispatch')
class MemoryManagementView(TemplateView):
    template_name = 'aiengine/memory_management.html'

    def get(self, request: HttpRequest, *args, **kwargs):
        try:
            # Get system-wide memory statistics
            system_stats = get_memory_statistics()
            
            # Get user-specific statistics
            user_stats = get_user_conversation_summary(request.user.id)
            
            # Get threads that need cleanup (old inactive threads)
            from datetime import datetime, timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            old_threads = ConversationThread.objects.filter(
                user=request.user,
                updated_at__lt=cutoff_date,
                is_active=False
            ).count()
            
            context = self.get_context_data(**kwargs)
            context.update({
                'system_stats': system_stats,
                'user_stats': user_stats,
                'old_threads': old_threads,
            })
            return self.render_to_response(context)
        except Exception as e:
            logger.error(f"Error loading memory management: {e}")
            messages.error(request, 'Unable to load memory management.')
            return redirect('aiengine:agent_detail')


@login_required
def cleanup_memory(request: HttpRequest):
    """AJAX view to clean up old memory."""
    if request.method == 'POST':
        try:
            days_old = int(request.POST.get('days_old', 30))
            keep_recent = int(request.POST.get('keep_recent', 50))
            
            # Perform cleanup
            cleanup_stats = cleanup_old_conversations(days_old=days_old, keep_recent_messages=keep_recent)
            
            return JsonResponse({
                'success': True,
                'message': f'Memory cleanup completed. Removed {cleanup_stats.get("messages_cleaned", 0)} messages from {cleanup_stats.get("threads_updated", 0)} threads.',
                'stats': cleanup_stats
            })
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Error during cleanup: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
def test_semantic_search(request: HttpRequest):
    """AJAX view to test semantic search functionality."""
    if request.method == 'POST':
        try:
            query = request.POST.get('query', '').strip()
            thread_id = request.POST.get('thread_id', '')
            
            if not query or not thread_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Query and thread ID are required'
                })
            
            # Get thread and perform semantic search
            thread = get_object_or_404(ConversationThread, thread_id=thread_id, user=request.user)
            from aiengine.memory_service import MemoryService
            memory_service = MemoryService(thread)
            
            relevant_messages = memory_service.get_relevant_messages(query, limit=5)
            
            results = []
            for msg in relevant_messages:
                results.append({
                    'content': msg.content[:200] + '...' if len(msg.content) > 200 else msg.content,
                    'message_type': msg.message_type,
                    'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return JsonResponse({
                'success': True,
                'query': query,
                'results': results,
                'count': len(results)
            })
            
        except Exception as e:
            logger.error(f"Error during semantic search test: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Error during search: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def admin_required(user):
    """Check if user is admin/staff."""
    return user.is_authenticated and user.is_staff

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(admin_required), name='dispatch')
class TokenDashboardView(TemplateView):
    template_name = 'aiengine/token_dashboard.html'

    def get(self, request: HttpRequest, *args, **kwargs):
        # Get time period from request
        days = int(request.GET.get('days', 30))
        
        # Get token statistics
        token_stats = get_token_statistics(days=days)
        
        # Get top users
        top_users = get_top_token_users(limit=10)
        
        context = self.get_context_data(**kwargs)
        context.update({
            'token_stats': token_stats,
            'top_users': top_users,
            'selected_days': days,
            'available_periods': [7, 30, 90, 365]
        })
        return self.render_to_response(context)


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(admin_required), name='dispatch')
class UserTokenDetailsView(TemplateView):
    template_name = 'aiengine/user_token_details.html'

    def get(self, request: HttpRequest, *args, **kwargs):
        user_id = kwargs.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        # Get time period from request
        days = int(request.GET.get('days', 30))
        
        # Get user's token statistics
        user_stats = get_token_statistics(user=user, days=days)
        user_summary = get_user_token_summary(user)
        
        # Get user's recent conversations
        recent_threads = ConversationThread.objects.filter(user=user).order_by('-updated_at')[:10]
        
        context = self.get_context_data(**kwargs)
        context.update({
            'target_user': user,
            'user_stats': user_stats,
            'user_summary': user_summary,
            'recent_threads': recent_threads,
            'selected_days': days,
            'available_periods': [7, 30, 90, 365]
        })
        return self.render_to_response(context)


@login_required
@user_passes_test(admin_required)
def token_export(request):
    """Export token usage data as JSON."""
    
    # Get time period from request
    days = int(request.GET.get('days', 30))
    
    # Get comprehensive token statistics
    token_stats = get_token_statistics(days=days)
    top_users = get_top_token_users(limit=50)
    
    export_data = {
        'export_date': datetime.now(timezone.utc).isoformat(),
        'period_days': days,
        'statistics': token_stats,
        'top_users': top_users
    }
    
    return JsonResponse(export_data, json_dumps_params={'indent': 2})


@login_required
@require_POST
def reengage_webhook(request: HttpRequest):
    """Re-engage agent for a specific webhook message with optional extra prompt."""
    try:
        message_id = request.POST.get('message_id', '').strip()
        extra_prompt = request.POST.get('extra_prompt', '').strip()
        if not message_id:
            return JsonResponse({'success': False, 'message': 'message_id is required'}, status=400)

        webhook = WebhookData.objects.filter(message_id=message_id, user=request.user).first()
        if not webhook:
            return JsonResponse({'success': False, 'message': 'Webhook not found or not owned by user'}, status=404)

        # Eligibility: no reply previously OR previous processing failed
        if not (getattr(webhook, 'can_reengage', False)):
            return JsonResponse({'success': False, 'message': 'Webhook not eligible for re-engagement'}, status=400)

        # Build context: original conversation + extra prompt
        reengage_text = webhook.conversation
        if extra_prompt:
            reengage_text = f"{reengage_text}\n\nAdditional context: {extra_prompt}"

        # Resolve user and agent
        user = webhook.user
        agent = Agent.objects.filter(user=user).order_by('-is_active', 'created_at').first()
        if not agent:
            return JsonResponse({'success': False, 'message': 'Agent not found'}, status=404)

        chat_assistant = ChatAssistant(
            thread_id=webhook.remote_jid,
            system_instructions=agent.system_prompt,
            user=user,
            agent=agent,
            remote_jid=webhook.remote_jid
        )

        response = chat_assistant.send_message(reengage_text)
        needs_reply = getattr(response, 'needs_reply', True)
        response_text = getattr(response, 'response_text', response.content)

        # Send if needed
        if needs_reply:
            from connections.services import evolution_api_service
            success, send_result = evolution_api_service.send_text_message(
                instance_name=webhook.instance,
                number=webhook.remote_jid,
                message=response_text,
                reply_to_message_id=webhook.message_id
            )
            if not success:
                return JsonResponse({'success': False, 'message': 'Failed to send WhatsApp message'}, status=502)

        # Update webhook record
        from django.utils import timezone as _tz
        webhook.response_text = response_text
        webhook.needs_reply = needs_reply
        webhook.is_processed = True
        if hasattr(webhook, 'last_processed_at'):
            webhook.last_processed_at = _tz.now()
        webhook.processing_attempts = getattr(webhook, 'processing_attempts', 0) + 1
        webhook.processing_error = None
        webhook.save()

        return JsonResponse({'success': True, 'needs_reply': needs_reply, 'response_text': response_text})
    except Exception as e:
        logger.error(f"Error in reengage_webhook: {e}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)