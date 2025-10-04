"""
WhatsApp Agent Service Module

This module provides a service for managing WhatsApp AI agents using Google's ADK framework.
It handles session management, agent creation, and query processing following ADK best practices.
"""

import asyncio
import logging
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.adk.agents import Agent
from google.genai import types

from base.env_config import DATABASE_URL, get_env_variable
from aiengine.tools import tool_manager

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
    """Configuration for WhatsApp Agent."""
    app_name: str = 'WhatsAppAgent'
    model_name: str = 'gemini-2.0-flash'
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
    
    def __init__(self, user_id: str, session_id: str, config: Optional[AgentConfig] = None):
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
            model_name=get_env_variable('AI_AGENT_MODEL_NAME', 'gemini-2.0-flash'),
            agent_name=get_env_variable('AI_AGENT_NAME', 'WhatsAppAgent'),
            agent_description=get_env_variable(
                'AI_AGENT_DESCRIPTION', 
                'WhatsAppAgent is a smart AI agent that helps answer WhatsApp queries.'
            ),
            agent_instructions=get_env_variable(
                'AI_AGENT_INSTRUCTIONS',
                '''You are a smart AI agent that helps answer WhatsApp queries with accuracy and helpfulness.

                    AVAILABLE TOOLS AND WHEN TO USE THEM:

                    1. get_current_time() - Use this tool when:
                    - User asks "What time is it?" or "What's the current time?"
                    - User asks "What date is it?" or "What day is today?"
                    - User asks about the current date and time
                    - User needs to know the current moment in time
                    - When you want to confirm the time, date, or day

                    2. send_whatsapp_message(message, number, instance_name) - Use this tool when:
                    - You want to reply to a whatsapp message
                    - ALWAYS provide the instance_name parameter from the conversation context

                    CRITICAL TOOL USAGE RULES:
                    - ALWAYS use get_current_time() when asked about time, date, or day
                    - ALWAYS use send_whatsapp_message() when you want to reply to a whatsapp message
                    - For send_whatsapp_message, you MUST provide the instance_name parameter from the conversation context
                    - The send_whatsapp_message tool returns a dictionary with success status and message details
                    - If a tool returns success: false, read the "message" field and inform the user about the specific issue
                    - Always provide helpful error messages to users when tools fail

                    TOOL RESPONSE HANDLING:
                    - If send_whatsapp_message returns {"success": false, "message": "..."}, inform the user about the specific error
                    - If send_whatsapp_message returns {"success": true, "message": "..."}, confirm the message was sent successfully
                    - Always be helpful and provide clear feedback about what happened

                    Remember: You have access to these tools and should use them whenever appropriate!'''
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
            app_name=self.config.app_name,
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
            tools=self.tools,
        )
    
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
            
            # Process query with timeout
            async with asyncio.timeout(timeout):
                async for event in self._runner.run_async(
                    user_id=self.user_id, 
                    session_id=self.session_id, 
                    new_message=content
                ):
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            final_response_text = event.content.parts[0].text
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