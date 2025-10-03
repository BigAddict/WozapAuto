"""
Views for the AI Engine application.

This module contains views for testing and interacting with the WhatsApp AI agent service.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any

from django.shortcuts import render
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from asgiref.sync import sync_to_async

from .services import WhatsAppAgentService, WhatsAppAgentError, AgentConfig

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


@login_required
def agent_status_view(request: HttpRequest):
    """
    Get the status and configuration of the agent service.
    
    Args:
        request: HTTP request object
        
    Returns:
        JSON response with agent status information
    """
    try:
        # Create a temporary service to get configuration info
        session_id = f"status_check_{uuid.uuid4().hex[:8]}"
        user_id = str(request.user.id)
        
        # Use context manager for proper cleanup
        async def get_status():
            async with WhatsAppAgentService(user_id, session_id).session_context() as service:
                return service.get_session_info()
        
        # Create a new event loop for this operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            status_info = loop.run_until_complete(get_status())
        finally:
            loop.close()
        
        return JsonResponse({
            'success': True,
            'status': status_info
        })
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to get agent status: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def agent_test_api(request: HttpRequest):
    """
    API endpoint for testing the agent without authentication (for external testing).
    
    Args:
        request: HTTP request object
        
    Returns:
        JSON response with agent's response
    """
    try:
        # Parse JSON data
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        user_id = data.get('user_id', 'test_user')
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query cannot be empty'
            }, status=400)
        
        # Generate unique session ID
        session_id = f"api_test_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Processing API agent test query: {query[:100]}...")
        
        # Create and run agent service
        async def process_query():
            async with WhatsAppAgentService(user_id, session_id).session_context() as service:
                return await service.process_query(query, timeout=30.0)
        
        # Create a new event loop for this operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(process_query())
        finally:
            loop.close()
        
        return JsonResponse({
            'success': True,
            'response': response,
            'session_id': session_id,
            'query': query,
            'user_id': user_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
        
    except WhatsAppAgentError as e:
        logger.error(f"WhatsApp Agent API error: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Agent error: {str(e)}'
        }, status=500)
        
    except Exception as e:
        logger.error(f"Unexpected error in agent API test: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)
