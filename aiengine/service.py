from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, trim_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Sequence, Optional, Dict, Any
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langgraph.graph import add_messages
from langgraph.runtime import Runtime
from typing import List

from aiengine.prompts import personalized_prompt
from aiengine.checkpointer import DatabaseCheckpointSaver
from knowledgebase.service import KnowledgeBaseService
from aiengine.models import AIResponse, AgentContext
from aiengine.memory_tools import MemorySearchTool
from typing_extensions import Annotated, TypedDict
from knowledgebase.tools import KnowledgeBaseTool
from aiengine.memory_service import MemoryService
from audit.services import AuditService
from dotenv import load_dotenv
import logging
import time
import os

from base.env_config import get_env_variable

logger = logging.getLogger("aiengine.service")

load_dotenv()
os.environ['GOOGLE_API_KEY'] = get_env_variable('GEMINI_API_KEY')
os.environ['LANGSMITH_TRACING'] = get_env_variable('LANGSMITH_TRACING')
os.environ['LANGSMITH_API_KEY'] = get_env_variable('LANGSMITH_API_KEY')
os.environ['LANGSMITH_PROJECT'] = get_env_variable('LANGSMITH_PROJECT')

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class ChatAssistant:
    def __init__(self, agent_context: AgentContext):
        """
        Initialize the ChatAssistant.

        Args:
            agent_context (AgentContext): The context of the agent.
        """
        self.context = agent_context
        self.config = {"configurable": {"thread_id": self.context.webhook_data.remote_jid}}
        
        # Initialize tool usage tracking flags
        self._knowledge_base_used = False
        self._search_performed = False
        
        # Get business from agent or user
        if self.context.get_business():
            self.business = self.context.get_business()
            logger.info(f"Business found in agent context: {self.business.name}")
        else:
            self.business = None
            if self.context.agent and hasattr(self.context.agent, 'business') and self.context.agent.business:
                self.business = self.context.agent.business
                logger.info(f"Business found in agent: {self.business.name}")
            elif self.context.user and hasattr(self.context.user, 'business_profile'):
                self.business = self.context.user.business_profile
                logger.info(f"Business found in user: {self.business.name}")

        self.business_id = str(self.business.id) if self.business else None
        
        # Initialize services
        self._init_services()

        # Initialize model
        self.model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        
        # Create agent using LangChain v3 patterns
        self._create_agent()

    def _init_services(self):
        """Initialize memory, checkpointer, and knowledge base services."""
        logger.info(f"Initializing services for user: {self.context.user.username}, agent: {self.context.agent.id}, remote_jid: {self.context.webhook_data.remote_jid[:3]}...{self.context.webhook_data.remote_jid[-3:]}")

        if self.context.user and self.context.agent and self.context.webhook_data.remote_jid:
            try:
                self.checkpointer = DatabaseCheckpointSaver(self.context.user, self.context.agent.id, self.context.webhook_data.remote_jid)
                self.memory_service = MemoryService(self.checkpointer.thread)
                self.memory_tools = MemorySearchTool(self.memory_service)
                self.knowledge_base_service = KnowledgeBaseService(user=self.context.user)
                self.knowledge_base_tool = KnowledgeBaseTool(user=self.context.user, callback=self._tool_callback)
                # Get the conversation thread for this user and remote_jid
                # from aiengine.models import ConversationThread
                # try:
                #     thread = ConversationThread.objects.get(user=user, remote_jid=remote_jid)
                # except ConversationThread.DoesNotExist:
                #     thread = None
                
                self.business_tool = None
                # self.business_tool = BusinessTool(user=user, thread=thread, callback=self._tool_callback)
                self.user = self.context.user
                self.agent = self.context.agent
                logger.info(f"Initialized services for user: {self.context.user.username}")
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
        
        # Create message trimming middleware
        @before_model
        def trim_message_history(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
            """Trim messages to fit within token limit before each model call.
            Preserves messages with images/multimodal content."""
            messages = state["messages"]
            
            # Only trim if we have messages
            if not messages:
                return None
            
            # Check if any messages have multimodal content (images)
            def has_multimodal_content(msg: BaseMessage) -> bool:
                """Check if message has images or other multimodal content."""
                if hasattr(msg, 'content_blocks') and msg.content_blocks:
                    return any(block.get('type') in ('image', 'audio', 'video') 
                             for block in msg.content_blocks)
                # Check content if it's a list (multimodal format)
                if isinstance(msg.content, list):
                    return any(isinstance(item, dict) and item.get('type') in ('image', 'audio', 'video')
                             for item in msg.content)
                return False
            
            # Find the index of the most recent message with images
            last_image_msg_idx = None
            for i in range(len(messages) - 1, -1, -1):
                if has_multimodal_content(messages[i]):
                    last_image_msg_idx = i
                    break
            
            # Trim messages to max 1000 tokens, keeping the most recent ones
            # Use endOn to ensure we keep complete message boundaries
            trimmed = trim_messages(
                messages=messages,
                max_tokens=1000,
                token_counter=self.model,
                strategy="last",
                allow_partial=True,
                include_system=True,
                start_on="human",
                end_on=["human", "tool", "ai"]
            )
            
            # Ensure the most recent message with images is preserved
            if last_image_msg_idx is not None:
                image_msg = messages[last_image_msg_idx]
                # Check if the trimmed list still contains the image message
                if image_msg not in trimmed:
                    # Image message was removed, add it back
                    # Insert before the last message to maintain context
                    if len(trimmed) > 0:
                        # Insert the image message before the last message
                        trimmed.insert(-1, image_msg)
                        logger.info(f"Preserved message with image at index {last_image_msg_idx}")
                    else:
                        trimmed.append(image_msg)
                        logger.info(f"Preserved message with image at index {last_image_msg_idx}")
            
            # Only return update if messages were actually trimmed or modified
            if len(trimmed) != len(messages) or trimmed != messages:
                logger.info(f"Trimmed messages from {len(messages)} to {len(trimmed)}")
                return {"messages": trimmed}
            
            return None
        
        # Create agent with tools and middleware
        self.app = create_agent(
            model=self.model,
            tools=tools,
            middleware=[personalized_prompt, trim_message_history],
            response_format=AIResponse,
            checkpointer=self.checkpointer
        )

    def send_message(self) -> AIMessage:
        """Send message and get AI response using LangChain agent."""
        message = self.context.webhook_data.conversation

        base64_file = self.context.webhook_data.base64_file
        if base64_file:
            mime_type = self.context.webhook_data.mime_type

        start_time = time.time()
        
        # Reset tool usage flags
        self._knowledge_base_used = False
        self._search_performed = False
        
        # Store human message
        self._store_human_message(self.context.webhook_data.conversation)

        human_message = self._get_human_message()

        # Get the agent response - trimming is handled by middleware
        output = self.app.invoke(
            {"messages": human_message},
            self.config,
            context=self.context
        )

        ai_response_message: AIMessage = output["messages"][-1]
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
        if self.context.user and self.context.agent and self.context.webhook_data.remote_jid:
            AuditService.log_ai_conversation(
                user=self.context.user,
                agent_id=self.context.agent.id,
                thread_id=self.context.webhook_data.remote_jid,
                remote_jid=self.context.webhook_data.remote_jid,
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

    def _get_human_message(self) -> list[BaseMessage]:
        message = self.context.webhook_data.conversation
        customer_name = self.context.webhook_data.push_name
        customer_phone = self.context.webhook_data.remote_jid.split('@')[0]

        prompt = f"Customer Name: {customer_name}\nCustomer Phone: {customer_phone}\n\n{message}"
        if self.context.webhook_data.base64_file:
            # Gemini API requires mime_type for base64 image data
            mime_type = self.context.webhook_data.mime_type
            if not mime_type:
                logger.warning("base64_file provided but mime_type is missing. Defaulting to image/jpeg")
                mime_type = "image/jpeg"
            
            return [HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image", "base64": self.context.webhook_data.base64_file, "mime_type": mime_type}
            ])]
        else:
            return [HumanMessage(content=prompt)]