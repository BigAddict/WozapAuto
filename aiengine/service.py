from langgraph.prebuilt import create_react_agent
from langgraph.graph import add_messages
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, trim_messages
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model

from aiengine.prompts import create_prompt_template
from aiengine.checkpointer import DatabaseCheckpointSaver
from aiengine.memory_service import MemoryService
from aiengine.memory_tools import MemorySearchTool
from aiengine.models import ConversationThread, Agent
from knowledgebase.service import KnowledgeBaseService
from knowledgebase.tools import KnowledgeBaseTool
from audit.services import AuditService
from typing_extensions import Annotated, TypedDict
from typing import Sequence, Optional, Dict, Any
from dotenv import load_dotenv
import logging
import os
import time

from base.env_config import get_env_variable

logger = logging.getLogger("aiengine.service")

load_dotenv()
os.environ['GOOGLE_API_KEY'] = get_env_variable('GOOGLE_API_KEY')
os.environ['LANGSMITH_TRACING'] = get_env_variable('LANGSMITH_TRACING')
os.environ['LANGSMITH_API_KEY'] = get_env_variable('LANGSMITH_API_KEY')

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class ChatAssistant:
    def __init__(self, thread_id: str, system_instructions: str, user=None, agent=None, remote_jid: str = None):
        self.thread_id = thread_id
        self.system_prompt = system_instructions
        self.model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
        self.config = {"configurable": {"thread_id": thread_id}}
        
        # Initialize tool usage tracking flags
        self._knowledge_base_used = False
        self._search_performed = False
        
        # Initialize services
        self._init_services(user, agent, remote_jid)
        
        # Create agent using LangChain v3 patterns
        self._create_agent()
        
        self.prompt_template = self.get_prompt_template()
        self.trimmer = self.message_trimmer()

    def _init_services(self, user, agent, remote_jid):
        """Initialize memory, checkpointer, and knowledge base services."""
        if user and agent and remote_jid:
            try:
                self.checkpointer = DatabaseCheckpointSaver(user, agent.id, remote_jid)
                self.memory_service = MemoryService(self.checkpointer.thread)
                self.memory_tools = MemorySearchTool(self.memory_service)
                self.knowledge_base_service = KnowledgeBaseService(user=user)
                self.knowledge_base_tool = KnowledgeBaseTool(user=user, callback=self._tool_callback)
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
        self.user = None
        self.agent = None
        logger.info("Initialized fallback services")
    
    def _tool_callback(self, tool_type: str, used: bool):
        """Callback to track tool usage."""
        if tool_type == 'knowledge_base_used':
            self._knowledge_base_used = used
        elif tool_type == 'search_performed':
            self._search_performed = used
    
    def _get_system_instructions(self) -> str:
        """Get the complete system instructions."""
        from aiengine.prompts import create_system_instructions
        return create_system_instructions(self.system_prompt)
    
    def _create_agent(self):
        """Create agent using LangGraph's create_react_agent."""
        tools = []
        
        # Add memory tools if available
        if self.memory_tools:
            tools.extend(self.memory_tools.get_tools())
        
        # Add knowledge base tool if available
        if hasattr(self, 'knowledge_base_tool') and self.knowledge_base_tool:
            tools.append(self.knowledge_base_tool.get_tool())
        
        logger.info(f"Creating agent with {len(tools)} tools")
        
        # Debug: Log the system instructions being used
        logger.info(f"System instructions: {self.system_prompt[:100]}...")
        logger.info(f"Prompt template created with system instructions")
        
        # Create agent with tools first, then we'll handle the prompt in send_message
        self.app = create_react_agent(
            model=self.model,
            tools=tools,
            checkpointer=self.checkpointer
        )

    def send_message(self, message: str) -> AIMessage:
        """Send message and get AI response using LangChain agent."""
        logger.info(f"Processing message: {message[:50]}...")
        start_time = time.time()
        
        # Reset tool usage flags
        self._knowledge_base_used = False
        self._search_performed = False
        
        # Store human message
        self._store_human_message(message)
        
        # Cleanup old messages if needed
        self._cleanup_messages_if_needed()
        
        # Create messages with system instructions
        system_message = SystemMessage(content=self._get_system_instructions())
        user_message = HumanMessage(content=message)
        input_messages = [system_message, user_message]
        
        logger.info(f"Sending to agent: {message[:100]}...")
        logger.debug(f"System instructions: {self.system_prompt[:200]}...")
        logger.debug(f"User message: {message}")
        
        output = self.app.invoke({"messages": input_messages}, self.config)
        ai_response = output["messages"][-1]
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Store AI response with audit logging
        self._store_ai_response(ai_response, response_time_ms)
        
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
    
    def _cleanup_messages_if_needed(self):
        """Cleanup old messages to prevent memory issues."""
        if self.memory_service:
            try:
                self.memory_service.cleanup_old_messages(keep_recent=50)
            except Exception as e:
                logger.warning(f"Failed to cleanup messages: {e}")

    def get_prompt_template(self) -> ChatPromptTemplate:
        """Get prompt template for the agent."""
        logger.info("Building prompt template")
        return create_prompt_template(self.system_prompt)
    
    def message_trimmer(
            self,
            max_tokens: int = 2000,  # Increased from 65 to handle longer conversations
            strategy: str = "last",
            token_counter: Optional[BaseChatModel] = None,
            include_system: bool = True,
            allow_partial: bool = False,
            start_on: str ="human",
    ):
        if token_counter is None:
            token_counter = self.model
        return trim_messages(
            max_tokens=max_tokens,
            strategy=strategy,
            token_counter=token_counter,
            include_system=include_system,
            allow_partial=allow_partial,
            start_on=start_on
        )
    
    
    
if __name__ == '__main__':
    # Test system instructions
    test_system_prompt = "You are a helpful AI assistant. Always respond with 'I understand' followed by the user's message."
    assistant = ChatAssistant("test_thread", test_system_prompt)
    
    # Test the system instructions
    test_message = "Hello, how are you?"
    print(f"Testing with message: {test_message}")
    print(f"System prompt: {assistant.system_prompt}")
    
    response = assistant.send_message(test_message)
    print(f"Response: {response.content}")