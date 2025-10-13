"""
WhatsApp Agent Service Module

This module provides a service for managing WhatsApp AI agents using Google's ADK framework.
It handles session management, agent creation, and query processing following ADK best practices.
"""

import asyncio
import logging
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager, aclosing

from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.adk.agents import Agent
from pgvector.django import CosineDistance
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from aiengine.embedding import EmbeddingService
from aiengine.models import KnowledgeBase, AgentResponse
from base.env_config import DATABASE_URL, get_env_variable
from aiengine.tools import tool_manager
from core.models import UserProfile
from aiengine.prompt import AgentInstructions

logger = logging.getLogger('aiengine.services')


class WhatsAppAgentError(Exception):
    """Base exception for WhatsApp Agent Service errors."""
    pass


class SessionCreationError(WhatsAppAgentError):
    """Raised when session creation fails."""
    pass


class AgentQueryError(WhatsAppAgentError):
    """Raised when agent query processing fails."""
    pass


class ConfigurationError(WhatsAppAgentError):
    """Raised when configuration is invalid."""
    pass


@dataclass
class AgentConfig:
    """
    Configuration for WhatsApp Agent.
    
    Attributes:
        app_name (str): Name of the WhatsApp agent app
        model_name (str): Name of the model to use for the agent
        agent_name (str): Name of the agent
        agent_description (str): Description of the agent
        agent_instructions (str): Instructions for the agent.
    """
    app_name: str = 'WhatsAppAgent'
    model_name: str = 'gemini-2.0-flash-lite'
    agent_name: str = 'WhatsAppAgent'
    agent_description: str = 'WhatsAppAgent is a smart AI agent that helps answer WhatsApp queries.'
    agent_instructions: str = 'You are a smart AI agent that helps answer WhatsApp queries with accuracy and helpfulness. Use the get_current_time tool to get the current time and the send_whatsapp_message tool to send messages to WhatsApp.'


class WhatsAppAgentService:
    """
    Service for managing WhatsApp AI agents using Google ADK.
    
    This service provides functionality to create and manage AI agents for WhatsApp
    interactions, following ADK best practices for simplicity and reliability.
    
    Attributes:
        config (AgentConfig): Configuration for the agent
        session_service (InMemorySessionService): Session service
        runner (Runner): Agent runner instance
        tools (List[Callable]): List of available tools for the agent
        
    Example:
        >>> service = WhatsAppAgentService("user123", "session456")
        >>> response = await service.process_query("Hello, how can you help me?")
        >>> print(response)
    """
    
    def __init__(self, user_id: str, session_id: str, config: Optional[AgentConfig] = None, app_name_override: Optional[str] = None, invocation_context: Optional[Dict[str, Any]] = None):
        """
        Initialize the WhatsApp Agent Service.
        
        Args:
            user_id (str): Unique identifier for the user
            session_id (str): Unique identifier for the session
            config (Optional[AgentConfig]): Configuration for the agent. If None, uses defaults.
            
        Raises:
            ConfigurationError: If required configuration is missing
            ValueError: If user_id or session_id are invalid
        """
        self._validate_inputs(user_id, session_id)
        
        self.config = config or self._load_config()
        self.user_id = user_id
        self.session_id = session_id
        self.tools: List[Callable] = tool_manager.get_all_tools()
        self._session_service: Optional[DatabaseSessionService] = None
        self._runner: Optional[Runner] = None
        self._invocation_context: Dict[str, Any] = invocation_context or {}
        self._app_name_override: Optional[str] = app_name_override
        
        logger.info(f"Initializing WhatsAppAgentService for user: {user_id}, session: {session_id}")
        
        # Initialize session service and runner
        self._initialize_service()
    
    def _validate_inputs(self, user_id: str, session_id: str) -> None:
        """
        Validate input parameters.
        
        Args:
            user_id (str): User identifier to validate
            session_id (str): Session identifier to validate
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        
        if not session_id or not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
    
    def _load_config(self) -> AgentConfig:
        """
        Load configuration from environment variables or use defaults.
        
        Returns:
            AgentConfig: Loaded configuration
        """
        return AgentConfig(
            app_name=get_env_variable('AI_AGENT_APP_NAME', 'WhatsAppAgent'),
            model_name=get_env_variable('AI_AGENT_MODEL_NAME', 'gemini-2.5-flash-lite'),
            agent_name=get_env_variable('AI_AGENT_NAME', 'WhatsAppAgent'),
            agent_description=get_env_variable(
                'AI_AGENT_DESCRIPTION', 
                'WhatsAppAgent is a smart AI agent that helps answer WhatsApp queries.'
            ),
            agent_instructions=get_env_variable(
                'AI_AGENT_INSTRUCTIONS',
                f'''
                {AgentInstructions}
                '''
                    )
                )
    
    def _initialize_service(self) -> None:
        """
        Initialize the session service and runner following ADK best practices.
        """
        # Initialize session service using InMemorySessionService for simplicity
        self._session_service = DatabaseSessionService(db_url=DATABASE_URL)
        
        # Initialize runner with the agent
        self._runner = Runner(
            agent=self._create_agent(),
            app_name=self._compute_app_name(),
            session_service=self._session_service
        )
        
        logger.info(f"Successfully initialized WhatsAppAgentService for user: {self.user_id}")
    
    async def _ensure_session_exists(self) -> None:
        """
        Ensure a session exists for the agent (lazy creation).
        """
        session = await self._session_service.get_session(
            app_name=self.config.app_name,
            user_id=self.user_id,
            session_id=self.session_id
        )
        if not session:
            session = await self._session_service.create_session(
                app_name=self.config.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )
            logger.debug(f"Created session for user: {self.user_id}, session: {self.session_id}")
    
    def _create_agent(self) -> Agent:
        """
        Create and configure the AI agent following ADK patterns.
        
        Returns:
            Agent: Configured agent instance
        """
        return Agent(
            name=self.config.agent_name,
            model=self.config.model_name,  # Add the required model parameter
            description=self.config.agent_description,
            instruction=self.config.agent_instructions,  # Use 'instruction' not 'instructions'
            output_schema=AgentResponse,
            tools=self.tools,
            before_model_callback=self._before_model_callback,
            before_tool_callback=self._before_tool_callback,
        )

    def _compute_app_name(self) -> str:
        base_name = self.config.app_name
        instance = (self._invocation_context or {}).get('instance')
        # if instance:
        #     return f"{base_name}:{instance}"
        return base_name

    def _sanitize_remote_jid(self, remote_jid: str, is_group: Optional[bool] = None) -> str:
        # For groups, Evolution expects the full group JID (e.g., 12345-67890@g.us)
        if is_group is None:
            is_group = remote_jid.endswith('@g.us')
        if is_group:
            return remote_jid
        # For individual chats, Evolution expects just the number (digits only)
        core = remote_jid.split('@')[0]
        return ''.join(ch for ch in core if ch.isdigit())

    def _before_model_callback(self, callback_context: CallbackContext, llm_request: LlmRequest):
        ctx = self._invocation_context or {}
        st = callback_context.state
        try:
            instance = ctx.get('instance')
            remote_jid = ctx.get('remote_jid')
            sender = ctx.get('sender')
            push_name = ctx.get('push_name')
            message_id = ctx.get('message_id')
            quoted_message = ctx.get('quoted_message')
            is_group = ctx.get('is_group')

            if instance:
                st["user:instance_name"] = instance
            if remote_jid:
                st["user:remote_jid"] = remote_jid
            if is_group is not None:
                st["user:is_group"] = bool(is_group)
            if push_name:
                st["user:push_name"] = push_name
            if sender:
                st["sender"] = sender
            if message_id:
                st["temp:message_id"] = message_id
            if quoted_message:
                st["temp:reply_to_message_id"] = quoted_message.get('stanzaId') or quoted_message.get('key', {}).get('id') or ''
        except Exception:
            pass
        return None

    def _before_tool_callback(self, tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext):
        try:
            if tool.name == "send_whatsapp_message":
                ctx = self._invocation_context or {}
                if not args.get('instance_name'):
                    inst = ctx.get('instance') or tool_context.state.get('app:instance_name')
                    if inst:
                        args['instance_name'] = inst
                if not args.get('number'):
                    rjid = ctx.get('remote_jid') or tool_context.state.get('user:remote_jid')
                    is_group = ctx.get('is_group')
                    if is_group is None:
                        is_group = tool_context.state.get('user:is_group')
                    if rjid:
                        args['number'] = self._sanitize_remote_jid(rjid, is_group=is_group)
                if not args.get('reply_to_message_id'):
                    reply = ctx.get('quoted_message_id') or tool_context.state.get('temp:reply_to_message_id')
                    if reply:
                        args['reply_to_message_id'] = reply
        except Exception:
            pass
        return None
    
    def add_tool(self, tool: Callable) -> None:
        """
        Add a tool to the agent's toolkit.
        
        Args:
            tool (Callable): Tool function to add
        """
        if not callable(tool):
            raise ValueError("Tool must be callable")
        
        self.tools.append(tool)
        logger.debug(f"Added tool: {tool.__name__}")
    
    def remove_tool(self, tool: Callable) -> bool:
        """
        Remove a tool from the agent's toolkit.
        
        Args:
            tool (Callable): Tool function to remove
            
        Returns:
            bool: True if tool was removed, False if not found
        """
        try:
            self.tools.remove(tool)
            logger.debug(f"Removed tool: {tool.__name__}")
            return True
        except ValueError:
            logger.warning(f"Tool not found: {tool.__name__}")
            return False
    
    async def process_query(self, query: str, timeout: Optional[float] = 30.0) -> str:
        """
        Process a query using the AI agent following ADK patterns.
        
        Args:
            query (str): The query to process
            timeout (Optional[float]): Timeout in seconds for the query processing
            
        Returns:
            str: The agent's response
            
        Raises:
            AgentQueryError: If query processing fails
            ValueError: If query is invalid
        """
        if not query or not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string")
        
        if not self._runner:
            raise AgentQueryError("Service not properly initialized")
        
        logger.info(f"Processing query for user: {self.user_id}, session: {self.session_id}")
        
        try:
            # Ensure session exists (lazy creation)
            await self._ensure_session_exists()
            
            content = types.Content(
                role='user',
                parts=[types.Part(text=query.strip())]
            )
            
            final_response_text = "Agent did not respond"
            
            # Process query with timeout and ensure generator is properly closed
            stream = self._runner.run_async(
                user_id=self.user_id,
                session_id=self.session_id,
                new_message=content
            )
            async with asyncio.timeout(timeout):
                async with aclosing(stream):
                    async for event in stream:
                        if event.is_final_response():
                            if event.content and event.content.parts:
                                # Handle both text and function_call parts
                                for part in event.content.parts:
                                    if part.text:
                                        final_response_text = part.text
                                    elif part.function_call:
                                        logger.info(f"Received function_call: {part.function_call.name} with args {part.function_call.args}")
                                        final_response_text = f"Agent made a function call: {part.function_call.name}"
                            elif event.actions and event.actions.escalate:
                                final_response_text = f"Agent escalated: {event.error_message}"
                            break
            
            logger.info(f"Query processed successfully for user: {self.user_id}")
            return final_response_text
            
        except asyncio.TimeoutError:
            error_msg = f"Query processing timed out after {timeout} seconds"
            logger.error(error_msg)
            raise AgentQueryError(error_msg)
        except Exception as e:
            error_msg = f"Query processing failed: {e}"
            logger.error(error_msg)
            raise AgentQueryError(error_msg) from e
    
    async def cleanup(self) -> None:
        """
        Clean up resources and close connections.
        """
        logger.info(f"Cleaning up session for user: {self.user_id}, session: {self.session_id}")
        self._session_service = None
        self._runner = None
        self._session_created = False
    
    @asynccontextmanager
    async def session_context(self):
        """
        Context manager for session lifecycle management.
        
        Yields:
            WhatsAppAgentService: The service instance
            
        Example:
            >>> async with WhatsAppAgentService("user123", "session456").session_context() as service:
            ...     response = await service.process_query("Hello!")
        """
        try:
            yield self
        finally:
            await self.cleanup()
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        Returns:
            Dict[str, Any]: Session information
        """
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'app_name': self.config.app_name,
            'model_name': self.config.model_name,
            'tools_count': len(self.tools),
            'session_created': self._session_created,
            'service_initialized': self._runner is not None,
            'session_service_ready': self._session_service is not None
        }
    
    def __repr__(self) -> str:
        """String representation of the service."""
        return f"WhatsAppAgentService(user_id='{self.user_id}', session_id='{self.session_id}')"
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        if hasattr(self, '_session_created') and self._session_created:
            try:
                # Schedule cleanup for next event loop iteration
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.cleanup())
                else:
                    loop.run_until_complete(self.cleanup())
            except Exception:
                # Ignore errors during destruction
                pass

def retrieve_knowledge(
    query: str,
    instance_name: str,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Retrieve the most relevant knowledge base chunks for the current tenant/user context.

    Args:
        query (str): Natural language query to search with.
        instance_name (str): Instance name to scope the search by.
        top_k (int): Number of results to return (default 5, max 20).

    Returns:
        Dict[str, Any]: {
            "success": bool,
            "results": [
                {"id": int, "score": float, "content": str, "metadata": dict, "original_filename": str, "chunk_index": int}
            ],
            "message": str
        }
    """
    try:
        top_k = int(top_k)
        if not query or not query.strip():
            return {"success": False, "message": "Query cannot be empty", "results": []}

        if top_k <= 0:
            top_k = 5
        if top_k > 20:
            top_k = 20

        # Scope by tenant; favor state 'app:instance_name'
        user_profile = UserProfile.objects.get(company_name=instance_name)
        user_id = user_profile.user.id

        # Generate embedding for the query (normalized to 1536 dims)
        emb = EmbeddingService()
        query_vec = emb.embed_text(query).embedding_vector

        # Base queryset: optionally filter by tenant via metadata.instance_name if present
        print(f"Before we hit qs")
        qs = KnowledgeBase.objects.filter(user_id=user_id)
        print(f"After we hit qs")
        # The following filter is redundant if we are already filtering by user_id
        # if instance_name:
        #     print(f"Before we hit qs filter")
        #     qs = qs.filter(metadata__instance_name=instance_name)
        #     print(f"After we hit qs filter")

        # Order by cosine distance to query vector (lower is closer)
        print(f"Before we hit annotate")
        qs = qs.annotate(distance=CosineDistance("embedding", query_vec)).order_by("distance")[:top_k]
        print(f"After we hit annotate")

        results = []
        for row in qs:
            print(f"Before we hit row")
            results.append({
                "id": row.id,
                "score": float(1.0 - getattr(row, "distance", 0.0)),  # similarity ~ 1 - distance
                "content": row.content,
                "metadata": row.metadata or {},
                "original_filename": row.original_filename or "",
                "chunk_index": row.chunk_index,
            })
            print(f"After we hit row")
        return {
            "success": True,
            "message": f"Retrieved {len(results)} result(s)",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in retrieve_knowledge: {e}")
        return {"success": False, "message": f"Retrieval failed: {str(e)}", "results": []}