from langchain.agents import create_agent
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, trim_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List

from aiengine.prompts import internal_system_instruction
from aiengine.checkpointer import DatabaseCheckpointSaver
from aiengine.memory_service import MemoryService
from aiengine.memory_tools import MemorySearchTool
from knowledgebase.service import KnowledgeBaseService
from knowledgebase.tools import KnowledgeBaseTool
from audit.services import AuditService
from typing_extensions import Annotated, TypedDict
from typing import Sequence, Optional, Dict
from aiengine.models import AIResponse
from dotenv import load_dotenv
import logging
import os
import time

from base.env_config import get_env_variable

logger = logging.getLogger("aiengine.service")

load_dotenv()
os.environ['GOOGLE_API_KEY'] = get_env_variable('GEMINI_API_KEY')
os.environ['LANGSMITH_TRACING'] = get_env_variable('LANGSMITH_TRACING')
os.environ['LANGSMITH_API_KEY'] = get_env_variable('LANGSMITH_API_KEY')

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class ChatAssistant:
    def __init__(self, thread_id: str, system_instructions: str, user=None, agent=None, remote_jid: str = None):
        """
        Initialize the ChatAssistant.

        Args:
            thread_id (str): The ID of the conversation thread.
            system_instructions (str): The system instructions for the agent.
            user (optional): The user object associated with the conversation.
            agent (optional): The agent object to use for responses.
            remote_jid (str, optional): The remote JID of the conversation.
        """
        logger.info(f"Initializing ChatAssistant for thread: {thread_id}")

        self.thread_id = thread_id
        self.system_prompt = system_instructions
        self.config = {"configurable": {"thread_id": thread_id}}
        
        # Initialize tool usage tracking flags
        self._knowledge_base_used = False
        self._search_performed = False
        
        # Get business from agent or user
        self.business = None
        if agent and hasattr(agent, 'business') and agent.business:
            self.business = agent.business
            logger.info(f"Business found in agent: {self.business.name}")
        elif user and hasattr(user, 'business_profile'):
            self.business = user.business_profile
            logger.info(f"Business found in user: {self.business.name}")

        self.business_id = str(self.business.id) if self.business else None
        
        # Initialize services
        self._init_services(user, agent, remote_jid)

        # Initialize model
        self.model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        
        # Create agent using LangChain v3 patterns
        self._create_agent()

    def _init_services(self, user, agent, remote_jid):
        """Initialize memory, checkpointer, and knowledge base services."""
        logger.info(f"Initializing services for user: {user.username}, agent: {agent.id}, remote_jid: {remote_jid[:3]}...{remote_jid[-3:]}")

        if user and agent and remote_jid:
            try:
                self.checkpointer = DatabaseCheckpointSaver(user, agent.id, remote_jid)
                self.memory_service = MemoryService(self.checkpointer.thread)
                self.memory_tools = MemorySearchTool(self.memory_service)
                self.knowledge_base_service = KnowledgeBaseService(user=user)
                self.knowledge_base_tool = KnowledgeBaseTool(user=user, callback=self._tool_callback)
                # Get the conversation thread for this user and remote_jid
                # from aiengine.models import ConversationThread
                # try:
                #     thread = ConversationThread.objects.get(user=user, remote_jid=remote_jid)
                # except ConversationThread.DoesNotExist:
                #     thread = None
                
                self.business_tool = None
                # self.business_tool = BusinessTool(user=user, thread=thread, callback=self._tool_callback)
                self.user = user
                self.agent = agent
                logger.info(f"Initialized services for user: {user.username}")
            except Exception as e:
                logger.error(f"Error initializing services: {e}")
                self._init_fallback_services()
        else:
            self._init_fallback_services()
    
    def _init_fallback_services(self):
        """Initialize fallback in-memory services."""
        from langgraph.checkpoint.memory import MemorySaver
        self.checkpointer = MemorySaver()
        self.memory_service = None
        self.memory_tools = None
        self.knowledge_base_service = None
        self.knowledge_base_tool = None
        self.business_tool = None
        self.user = None
        self.agent = None
        logger.info("Initialized fallback services")
    
    def _tool_callback(self, tool_type: str, used: bool):
        """Callback to track tool usage."""
        if tool_type == 'knowledge_base_used':
            self._knowledge_base_used = used
        elif tool_type == 'search_performed':
            self._search_performed = used
    
    def _get_internal_system_instructions(self) -> str:
        """Get the complete system instructions with user's timezone."""
        return internal_system_instruction(
            user=self.user if hasattr(self, 'user') else None,
            business=self.business if hasattr(self, 'business') else None
        )
    
    def _create_agent(self):
        """Create agent using LangGraph's create_agent function."""
        tools = []
        
        # Add memory tools if available
        if self.memory_tools:
            tools.extend(self.memory_tools.get_tools())
            logger.info(f"Added memory tools: {len(self.memory_tools.get_tools())}")
        
        # Add knowledge base tool if available
        if hasattr(self, 'knowledge_base_tool') and self.knowledge_base_tool:
            tools.append(self.knowledge_base_tool.get_tool())
            logger.info(f"Added knowledge base tool")

        # Add business tools if available
        if hasattr(self, 'business_tool') and self.business_tool:
            tools.extend(self.business_tool.get_tools())
            logger.info(f"Added business tools: {len(self.business_tool.get_tools())}")
        
        logger.info(f"Creating agent with {len(tools)} tools")
        
        # Create agent with tools
        self.app = create_agent(
            model=self.model,
            tools=tools,
            system_prompt = self._get_internal_system_instructions(),
            response_format=AIResponse,
            checkpointer=self.checkpointer
        )

    def send_message(self, message: str, base64_file: Optional[str] = None, mime_type: Optional[str] = None) -> AIMessage:
        """Send message and get AI response using LangChain agent."""
        logger.info(f"Processing message: {message[:50]}...")
        start_time = time.time()
        
        # Reset tool usage flags
        self._knowledge_base_used = False
        self._search_performed = False
        
        # Store human message
        self._store_human_message(message)
        
        # Create messages with system instructions
        system_message = SystemMessage(content=self.system_prompt)

        if base64_file:
            # Gemini API requires mime_type for base64 image data
            if not mime_type:
                logger.warning("base64_file provided but mime_type is missing. Defaulting to image/jpeg")
                mime_type = "image/jpeg"
            
            human_message = HumanMessage(content=[
                {"type": "text", "text": message},
                {"type": "image", "base64": base64_file, "mime_type": mime_type}
            ])
        else:
            human_message = HumanMessage(content=message)

        messages = self.message_trimmer([system_message, human_message])
        
        # Get the agent response
        output = self.app.invoke({"messages": messages}, self.config)

        ai_response_message = output["messages"][-1]
        structured_output: AIResponse = output["structured_response"]
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Store AI response with audit logging
        ai_response = AIMessage(
            content=structured_output.response_text,
            response_metadata=getattr(ai_response_message, 'response_metadata', {})
        )
        self._store_ai_response(ai_response, response_time_ms)
        
        # Attach structured fields to the message for callers to use
        setattr(ai_response, "needs_reply", structured_output.needs_reply)
        setattr(ai_response, "response_text", structured_output.response_text)
        return ai_response

    def _store_human_message(self, message: str):
        """Store human message in memory service."""
        if self.memory_service:
            self.memory_service.add_message('human', message)
            logger.debug("Stored human message")
    
    def _store_ai_response(self, response: AIMessage, response_time_ms: int):
        """Store AI response with token tracking and audit logging."""
        if not self.memory_service:
            return
        
        # Extract token usage
        token_usage = self._extract_token_usage(response)
        
        # Store in memory
        self.memory_service.add_message('ai', response.content, token_usage=token_usage)
        
        # Audit logging
        if hasattr(self, 'user') and self.user:
            AuditService.log_ai_conversation(
                user=self.user,
                agent_id=self.agent.id if hasattr(self, 'agent') else None,
                thread_id=self.thread_id,
                remote_jid=getattr(self.memory_service.thread, 'remote_jid', ''),
                message_type='ai',
                input_tokens=token_usage.get('input_tokens') if token_usage else None,
                output_tokens=token_usage.get('output_tokens') if token_usage else None,
                total_tokens=token_usage.get('total_tokens') if token_usage else None,
                model_name=token_usage.get('model_name') if token_usage else 'gemini-2.5-flash',
                response_time_ms=response_time_ms,
                search_performed=self._search_performed,
                knowledge_base_used=self._knowledge_base_used,
                metadata={'message_length': len(response.content) if response.content else 0}
            )
    
    def _extract_token_usage(self, response: AIMessage) -> Optional[Dict]:
        """Extract token usage from AI response."""
        if hasattr(response, 'response_metadata') and response.response_metadata:
            usage_metadata = response.response_metadata.get('usage_metadata', {})
            if usage_metadata:
                return {
                    'input_tokens': usage_metadata.get('input_tokens'),
                    'output_tokens': usage_metadata.get('output_tokens'),
                    'total_tokens': usage_metadata.get('total_tokens'),
                    'model_name': response.response_metadata.get('model_name', 'gemini-2.5-flash')
                }
        return None
    
    def message_trimmer(self, messages: List[BaseMessage]) -> list[BaseMessage]:
        """Trim messages to have at most 2000 tokens."""
        return trim_messages(
            messages=messages,
            max_tokens=2000,
            token_counter=self.model,
            strategy="last",
            allow_partial=True,
            include_system=True
        )