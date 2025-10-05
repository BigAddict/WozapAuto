"""
Views for the AI Engine application.

This module contains views for testing and interacting with the WhatsApp AI agent service.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django.views import View
from django.views.generic import TemplateView
from asgiref.sync import sync_to_async

from .services import WhatsAppAgentService, WhatsAppAgentError, AgentConfig
from aiengine.embedding import EmbeddingService
from .models import Agent, WebhookData, EvolutionWebhookData, KnowledgeBase, DocumentMetadata
from .forms import PDFUploadForm, KnowledgeBaseDeleteForm
from core.models import UserProfile

logger = logging.getLogger('aiengine.views')


class AgentTestView(View):
    """
    View for testing the WhatsApp AI agent service.
    
    Provides both GET (display form) and POST (process queries) functionality.
    """
    
    @method_decorator(login_required)
    def get(self, request: HttpRequest):
        """
        Display the agent testing interface.
        
        Args:
            request: HTTP request object
            
        Returns:
            Rendered HTML template with agent testing form
        """
        context = {
            'title': 'WhatsApp AI Agent Test',
            'user': request.user,
        }
        return render(request, 'aiengine/agent_test.html', context)
    
    @method_decorator(login_required)
    def post(self, request: HttpRequest):
        """
        Process agent queries via AJAX.
        
        Args:
            request: HTTP request object containing query data
            
        Returns:
            JSON response with agent's response or error message
        """
        try:
            # Parse JSON data
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            
            if not query:
                return JsonResponse({
                    'success': False,
                    'error': 'Query cannot be empty'
                }, status=400)
            
            # Generate unique session ID for this test
            session_id = f"test_session_{uuid.uuid4().hex[:8]}"
            user_id = str(request.user.id)
            
            logger.info(f"Processing agent test query for user {user_id}: {query[:100]}...")
            
            # Create and run agent service using sync_to_async
            response = self._run_async_agent_query(user_id, session_id, query)
            
            return JsonResponse({
                'success': True,
                'response': response,
                'session_id': session_id,
                'query': query
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
            
        except WhatsAppAgentError as e:
            logger.error(f"WhatsApp Agent error: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Agent error: {str(e)}'
            }, status=500)
            
        except Exception as e:
            logger.error(f"Unexpected error in agent test: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }, status=500)
    
    def _run_async_agent_query(self, user_id: str, session_id: str, query: str) -> str:
        """
        Run async agent query in a new event loop.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            query: Query to process
            
        Returns:
            Agent's response string
        """
        try:
            # Create a new event loop for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._process_agent_query(user_id, session_id, query))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error running async agent query: {e}")
            raise

    async def _process_agent_query(self, user_id: str, session_id: str, query: str) -> str:
        """
        Process a query using the WhatsApp agent service.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            query: Query to process
            
        Returns:
            Agent's response string
        """
        try:
            # Create agent service with context manager for proper cleanup
            async with WhatsAppAgentService(user_id, session_id).session_context() as service:
                response = await service.process_query(query, timeout=30.0)
                return response
                
        except Exception as e:
            logger.error(f"Error processing agent query: {e}")
            raise

class AgentDetailsView(TemplateView):
    """
    View for displaying the details of the agent.
    """
    template_name = 'aiengine/agent_details.html'

    def get(self, request: HttpRequest, *args, **kwargs):
        self.user = request.user
        self.agent = Agent.objects.filter(user=self.user).first()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agent'] = self.agent
        return context

@method_decorator(csrf_exempt, name='dispatch')
class EvolutionWebhookView(View):
    """
    Class based webhook endpoint for receiving messages from Evolution API.
    """

    def post(self, request: HttpRequest):
        try:
            data = json.loads(request.body.decode('utf-8'))
            if not data and not data.get('event', ''):
                return JsonResponse({'success': True})

            payload = data.get('data', {})
            key = payload.get('key', {})
            context_info = payload.get('contextInfo', {})
            quoted_message = context_info.get('quotedMessage', {})

            date_time_val = payload.get('messageTimestamp')
            try:
                date_time_ext = datetime.fromtimestamp(date_time_val, tz=timezone.utc) if date_time_val else None
            except Exception:
                date_time_ext = datetime.now(timezone.utc)

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
            self._process_evolution_webhook_data(evolution_webhook_data)
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def _process_evolution_webhook_data(self, data: EvolutionWebhookData):
        try:
            self.save_to_db(data)
            response = self._run_async_agent_query(data.remote_jid, data.sender, self._apply_prompt_template(data))
            self.update_db_with_response(data, response)
        except Exception as e:
            logger.error(f"Error processing evolution webhook data: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def _get_user_from_instance_id(self, instance_id: str) -> Optional[User]:
        try:
            from connections.models import Connection
            connection = Connection.objects.get(instance_id=instance_id)
            return connection.user
        except Exception as e:
            return None

    def _apply_prompt_template(self, data: EvolutionWebhookData) -> str:
        prompt_template = f"""
        Instance name: {data.instance}
        WhatsApp name: {data.push_name}
        WhatsApp number: {data.remote_jid}
        WhatsApp message: {data.conversation}
        Message ID: {data.message_id}
        Is message from me: {data.from_me}
        A reply to: {data.quoted_message if data.quoted_message else "None"} if there is a reply to a message, otherwise None
        
        IMPORTANT: When you need to send a WhatsApp message, use the instance name "{data.instance}" in the send_whatsapp_message tool.
        """
        print(prompt_template, "\n")
        return prompt_template

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
            return True
        except Exception as e:
            return False

    def update_db_with_response(self, data: EvolutionWebhookData, response: str) -> bool:
        try:
            webhook_data = WebhookData.objects.get(message_id=data.message_id)
            webhook_data.response_text = response
            webhook_data.is_processed = True
            webhook_data.save()
            return True
        except Exception as e:
            return False

    def _run_async_agent_query(self, user_id: str, session_id: str, query: str) -> str:
        """
        Run async agent query in a new event loop.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            query: Query to process
            
        Returns:
            Agent's response string
        """
        try:
            # Create a new event loop for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._process_agent_query(user_id, session_id, query))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error running async agent query: {e}")
            raise

    async def _process_agent_query(self, user_id: str, session_id: str, query: str) -> str:
        """
        Process a query using the WhatsApp agent service.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            query: Query to process
            
        Returns:
            Agent's response string
        """
        try:
            # Create agent service with context manager for proper cleanup
            async with WhatsAppAgentService(user_id, session_id).session_context() as service:
                response = await service.process_query(query, timeout=30.0)
                return response
                
        except Exception as e:
            logger.error(f"Error processing agent query: {e}")
            raise

@method_decorator(login_required, name='dispatch')
class KnowledgeBaseManagementView(View):
    """
    View for managing knowledge base - uploading PDFs and managing existing files.
    """
    
    def get(self, request: HttpRequest):
        """
        Display the knowledge base management interface.
        
        Args:
            request: HTTP request object
            
        Returns:
            Rendered HTML template with knowledge base management form
        """
        # Get user's knowledge base entries
        knowledge_base_entries = KnowledgeBase.objects.filter(user=request.user).order_by('-created_at')
        
        # Group entries by original filename for better display
        grouped_entries = {}
        for entry in knowledge_base_entries:
            filename = entry.original_filename or entry.name
            info = grouped_entries.get(filename)
            if not info:
                info = {
                    'entries': [],
                    'total_chunks': 0,
                    'file_size': entry.file_size or 0,
                    'created_at': entry.created_at,
                    'description': None,
                }
                grouped_entries[filename] = info

            info['entries'].append(entry)
            info['total_chunks'] += 1

            # Prefer user-provided description; ignore autogenerated "Chunk N of <file>"
            if not info['description'] and entry.description:
                auto_prefix = 'Chunk '
                if not (entry.description.startswith(auto_prefix) and ' of ' in entry.description and entry.description.endswith(filename)):
                    info['description'] = entry.description
        
        context = {
            'title': 'Knowledge Base Management',
            'user': request.user,
            'upload_form': PDFUploadForm(user=request.user),
            'delete_form': KnowledgeBaseDeleteForm(),
            'grouped_entries': grouped_entries,
            'total_files': len(grouped_entries),
            'total_entries': knowledge_base_entries.count(),
        }
        return render(request, 'aiengine/knowledge_base_management.html', context)
    
    def post(self, request: HttpRequest):
        """
        Handle knowledge base operations (upload/delete).
        
        Args:
            request: HTTP request object containing form data
            
        Returns:
            JSON response or redirect
        """
        action = request.POST.get('action', '')
        
        if action == 'upload':
            return self._handle_upload(request)
        elif action == 'delete':
            return self._handle_delete(request)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action specified'
            }, status=400)
    
    def _handle_upload(self, request: HttpRequest):
        """Handle PDF file uploads."""
        try:
            form = PDFUploadForm(request.POST, request.FILES, user=request.user)
            
            if form.is_valid():
                files = form.cleaned_data['pdf_files']
                description = form.cleaned_data.get('description', '')
                
                # Process each file
                uploaded_files = []
                embedding_service = EmbeddingService()
                
                for file in files:
                    try:
                        # Generate unique file ID for tracking chunks
                        file_id = f"{request.user.id}_{uuid.uuid4().hex[:8]}"
                        
                        # Process PDF and generate embeddings
                        results = embedding_service.embed_pdf_file(
                            file_data=file,
                            metadata=DocumentMetadata(
                                name=file.name,
                                description=description or f"Uploaded PDF: {file.name}",
                                metadata={
                                    "user_id": request.user.id,
                                    "file_id": file_id,
                                    "upload_source": "web_interface"
                                }
                            )
                        )
                        
                        # Save each chunk to database
                        for i, result in enumerate(results):
                            knowledge_entry = KnowledgeBase.objects.create(
                                user=request.user,
                                name=f"{file.name} - Chunk {i+1}",
                                # Store only the user-provided description (omit autogenerated per-chunk text)
                                description=description or None,
                                content=result.source_chunk,
                                embedding=result.embedding_vector,
                                metadata=result.metadata,
                                original_filename=file.name,
                                file_size=file.size,
                                file_type='pdf',
                                chunk_index=i,
                                parent_file_id=file_id
                            )
                        
                        uploaded_files.append({
                            'filename': file.name,
                            'chunks': len(results),
                            'size': file.size
                        })
                        
                        logger.info(f"Successfully processed PDF {file.name} for user {request.user.id}: {len(results)} chunks")
                        
                    except Exception as e:
                        logger.error(f"Error processing PDF {file.name}: {e}")
                        return JsonResponse({
                            'success': False,
                            'error': f'Error processing {file.name}: {str(e)}'
                        }, status=500)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully uploaded {len(uploaded_files)} files',
                    'uploaded_files': uploaded_files
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Form validation failed',
                    'errors': form.errors
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error in PDF upload: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }, status=500)
    
    def _handle_delete(self, request: HttpRequest):
        """Handle knowledge base entry deletion."""
        try:
            form = KnowledgeBaseDeleteForm(request.POST)
            
            if form.is_valid():
                entry_ids = form.cleaned_data['entry_ids']
                
                # Get entries to delete
                entries_to_delete = KnowledgeBase.objects.filter(
                    id__in=entry_ids,
                    user=request.user
                )
                
                if not entries_to_delete.exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'No entries found to delete'
                    }, status=404)
                
                # Count files that will be deleted
                deleted_files = set()
                deleted_count = 0
                
                for entry in entries_to_delete:
                    if entry.original_filename:
                        deleted_files.add(entry.original_filename)
                    deleted_count += 1
                
                # Delete entries
                entries_to_delete.delete()
                
                logger.info(f"Deleted {deleted_count} knowledge base entries for user {request.user.id}")
                
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully deleted {deleted_count} entries from {len(deleted_files)} files',
                    'deleted_files': list(deleted_files)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Form validation failed',
                    'errors': form.errors
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error deleting knowledge base entries: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Deletion failed: {str(e)}'
            }, status=500)