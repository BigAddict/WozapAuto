from langgraph.graph import START, MessagesState, StateGraph, add_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, trim_messages
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model

from aiengine.prompts import text_formatting_guide
from aiengine.checkpointer import DatabaseCheckpointSaver
from aiengine.memory_service import MemoryService
from aiengine.memory_tools import MemorySearchTool
from aiengine.models import ConversationThread, Agent
from knowledgebase.service import KnowledgeBaseService
from audit.services import AuditService
from typing_extensions import Annotated, TypedDict
from typing import Sequence, Optional
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
        
        # Initialize database-backed memory if user and agent are provided
        if user and agent and remote_jid:
            try:
                self.checkpointer = DatabaseCheckpointSaver(user, agent.id, remote_jid)
                self.memory_service = MemoryService(self.checkpointer.thread)
                # Initialize memory tools
                self.memory_tools = MemorySearchTool(self.memory_service)
                # Initialize knowledge base service with user
                self.knowledge_base_service = KnowledgeBaseService(user=user)
            except Exception as e:
                logger.error(f"Error initializing database-backed memory: {e}")
                # Fallback to in-memory storage
                from langgraph.checkpoint.memory import MemorySaver
                self.checkpointer = MemorySaver()
                self.memory_service = None
                self.memory_tools = None
                self.knowledge_base_service = None
        else:
            # Fallback to in-memory storage for backward compatibility
            from langgraph.checkpoint.memory import MemorySaver
            self.checkpointer = MemorySaver()
            self.memory_service = None
            self.memory_tools = None
            self.knowledge_base_service = None
        
        self.prompt_template = self.get_prompt_template()
        self.init_workflow()
        self.trimmer = self.message_trimmer()

    def init_workflow(self):
        logger.info("Initializing workflow")
        self.workflow = StateGraph(state_schema=State)
        
        # Add memory tools if available
        if self.memory_tools:
            # Bind tools to the model
            self.model_with_tools = self.model.bind_tools(self.memory_tools.get_tools())
            self.workflow.add_node("model", self.call_model_with_tools)
        else:
            self.model_with_tools = self.model
            self.workflow.add_node("model", self.call_model)
        
        self.workflow.add_edge(START, "model")
        self.app = self.workflow.compile(checkpointer=self.checkpointer)

    def send_message(self, message: str) -> AIMessage:
        logger.info(f"Sending message: {message}")
        
        # Start timing for response time tracking
        start_time = time.time()
        
        # Store human message in database if memory service is available
        if self.memory_service:
            self.memory_service.add_message('human', message)
        
        # Clean up old messages to prevent timeout issues
        if self.memory_service:
            try:
                # Keep only the last 50 messages to prevent memory issues
                self.memory_service.cleanup_old_messages(keep_recent=50)
            except Exception as e:
                logger.warning(f"Failed to cleanup old messages: {e}")
        
        input_messages = [HumanMessage(message)]
        output = self.app.invoke({"messages": input_messages}, self.config)
        ai_response = output["messages"][-1]
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Store AI response in database if memory service is available
        if self.memory_service:
            # Extract token usage information from response
            token_usage = None
            if hasattr(ai_response, 'response_metadata') and ai_response.response_metadata:
                usage_metadata = ai_response.response_metadata.get('usage_metadata', {})
                if usage_metadata:
                    token_usage = {
                        'input_tokens': usage_metadata.get('input_tokens'),
                        'output_tokens': usage_metadata.get('output_tokens'),
                        'total_tokens': usage_metadata.get('total_tokens'),
                        'model_name': ai_response.response_metadata.get('model_name', 'gemini-2.5-flash')
                    }
            
            self.memory_service.add_message('ai', ai_response.content, token_usage=token_usage)
            
            # Log AI conversation for audit/analytics
            try:
                # Get user and agent info for logging
                user = getattr(self.memory_service, 'user', None)
                agent = getattr(self.memory_service, 'agent', None)
                thread = getattr(self.memory_service, 'thread', None)
                
                if user:
                    # Log the AI response
                    AuditService.log_ai_conversation(
                        user=user,
                        agent_id=agent.id if agent else None,
                        thread_id=thread.thread_id if thread else self.thread_id,
                        remote_jid=getattr(thread, 'remote_jid', '') if thread else '',
                        message_type='ai',
                        input_tokens=token_usage.get('input_tokens') if token_usage else None,
                        output_tokens=token_usage.get('output_tokens') if token_usage else None,
                        total_tokens=token_usage.get('total_tokens') if token_usage else None,
                        model_name=token_usage.get('model_name') if token_usage else 'gemini-2.5-flash',
                        response_time_ms=response_time_ms,
                        conversation_turn=getattr(self, '_conversation_turn', 1),
                        search_performed=getattr(self, '_search_performed', False),
                        knowledge_base_used=getattr(self, '_knowledge_base_used', False),
                        metadata={
                            'message_length': len(message),
                            'response_length': len(ai_response.content) if ai_response.content else 0
                        }
                    )
                    
                    # Log the human message as well
                    AuditService.log_ai_conversation(
                        user=user,
                        agent_id=agent.id if agent else None,
                        thread_id=thread.thread_id if thread else self.thread_id,
                        remote_jid=getattr(thread, 'remote_jid', '') if thread else '',
                        message_type='human',
                        conversation_turn=getattr(self, '_conversation_turn', 1),
                        metadata={
                            'message_length': len(message)
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to log AI conversation: {e}")
        
        return ai_response

    def call_model(self, state: State):
        logger.info(f"Calling model with state: {state}")
        
        # Get context messages using semantic search if memory service is available
        if self.memory_service and state.get('messages'):
            # Extract the latest human message for semantic search
            latest_human_message = None
            for msg in reversed(state['messages']):
                if isinstance(msg, HumanMessage):
                    latest_human_message = msg.content
                    break
            
            # Get only the last 5 messages for context (no semantic search by default)
            context_messages = self.memory_service.get_context_messages(
                query=None,  # No semantic search by default
                include_recent=True,
                include_semantic=False,  # Disable semantic search in context
                max_messages=5  # Only last 5 messages
            )
            
            # Combine context with current messages
            if context_messages:
                # Remove duplicates and combine
                existing_contents = {msg.content for msg in state['messages']}
                unique_context = [msg for msg in context_messages if msg.content not in existing_contents]
                state["messages"] = unique_context + state['messages']
        
        # Add knowledge base context if available
        if self.knowledge_base_service and state.get('messages'):
            # Extract the latest human message for knowledge base search
            latest_human_message = None
            for msg in reversed(state['messages']):
                if isinstance(msg, HumanMessage):
                    latest_human_message = msg.content
                    break
            
            if latest_human_message and self._should_search_knowledge_base(latest_human_message):
                try:
                    # Use settings from knowledge base service
                    settings = self.knowledge_base_service.settings
                    max_chunks = settings.max_chunks_in_context if settings else 3
                    min_similarity = settings.similarity_threshold if settings else 0.5
                    kb_context = self.get_knowledge_base_context(latest_human_message, max_chunks=max_chunks, min_similarity=min_similarity)
                    if kb_context:
                        # Add knowledge base context as a system message
                        kb_system_msg = SystemMessage(content=f"Relevant information from knowledge base:\n\n{kb_context}")
                        state["messages"] = [kb_system_msg] + state['messages']
                        logger.info("Added knowledge base context to conversation")
                except Exception as e:
                    logger.error(f"Error adding knowledge base context: {e}")
        
        # Trim messages to fit context window with safety checks
        try:
            # Check if we have too many messages and trim manually first
            if len(state['messages']) > 100:
                logger.warning(f"Large conversation detected ({len(state['messages'])} messages), pre-trimming")
                # Keep only the last 50 messages before applying token-based trimming
                state['messages'] = state['messages'][-50:]
            
            state["messages"] = self.trimmer.invoke(state['messages'])
        except Exception as e:
            logger.error(f"Error during message trimming: {e}")
            # Fallback: keep only the last 20 messages
            state["messages"] = state['messages'][-20:] if len(state['messages']) > 20 else state['messages']
        prompt = self.prompt_template.invoke(state)
        response = self.model.invoke(prompt)
        return {"messages": response}
    
    def call_model_with_tools(self, state: State):
        """Call model with memory tools available."""
        logger.info(f"Calling model with tools, state: {state}")
        
        # Get only the last 5 messages for context (no semantic search by default)
        if self.memory_service and state.get('messages'):
            context_messages = self.memory_service.get_context_messages(
                query=None,  # No semantic search by default
                include_recent=True,
                include_semantic=False,  # Disable semantic search in context
                max_messages=5  # Only last 5 messages
            )
            
            # Combine context with current messages
            if context_messages:
                # Remove duplicates and combine
                existing_contents = {msg.content for msg in state['messages']}
                unique_context = [msg for msg in context_messages if msg.content not in existing_contents]
                state["messages"] = unique_context + state['messages']
        
        # Add knowledge base context if available
        if self.knowledge_base_service and state.get('messages'):
            # Extract the latest human message for knowledge base search
            latest_human_message = None
            for msg in reversed(state['messages']):
                if isinstance(msg, HumanMessage):
                    latest_human_message = msg.content
                    break
            
            if latest_human_message and self._should_search_knowledge_base(latest_human_message):
                try:
                    # Use settings from knowledge base service
                    settings = self.knowledge_base_service.settings
                    max_chunks = settings.max_chunks_in_context if settings else 3
                    min_similarity = settings.similarity_threshold if settings else 0.5
                    kb_context = self.get_knowledge_base_context(latest_human_message, max_chunks=max_chunks, min_similarity=min_similarity)
                    if kb_context:
                        # Add knowledge base context as a system message
                        kb_system_msg = SystemMessage(content=f"Relevant information from knowledge base:\n\n{kb_context}")
                        state["messages"] = [kb_system_msg] + state['messages']
                        logger.info("Added knowledge base context to conversation")
                except Exception as e:
                    logger.error(f"Error adding knowledge base context: {e}")
        
        # Trim messages to fit context window with safety checks
        try:
            # Check if we have too many messages and trim manually first
            if len(state['messages']) > 100:
                logger.warning(f"Large conversation detected ({len(state['messages'])} messages), pre-trimming")
                # Keep only the last 50 messages before applying token-based trimming
                state['messages'] = state['messages'][-50:]
            
            state["messages"] = self.trimmer.invoke(state['messages'])
        except Exception as e:
            logger.error(f"Error during message trimming: {e}")
            # Fallback: keep only the last 20 messages
            state["messages"] = state['messages'][-20:] if len(state['messages']) > 20 else state['messages']
        prompt = self.prompt_template.invoke(state)
        
        # Use model with tools
        response = self.model_with_tools.invoke(prompt)
        
        # Handle tool calls if any
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"Model requested tool calls: {[tc['name'] for tc in response.tool_calls]}")
            
            # Add the model's response to messages
            messages = state["messages"] + [response]
            
            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                # Get the tool function
                tool_func = getattr(self.memory_tools, tool_name, None)
                if tool_func:
                    try:
                        # Execute the tool
                        tool_result = tool_func.invoke(tool_args)
                        
                        # Add tool result as a message
                        from langchain_core.messages import ToolMessage
                        tool_message = ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_call['id']
                        )
                        messages.append(tool_message)
                        
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}")
                        from langchain_core.messages import ToolMessage
                        error_message = ToolMessage(
                            content=f"Error executing {tool_name}: {str(e)}",
                            tool_call_id=tool_call['id']
                        )
                        messages.append(error_message)
                else:
                    logger.error(f"Tool {tool_name} not found")
                    from langchain_core.messages import ToolMessage
                    error_message = ToolMessage(
                        content=f"Tool {tool_name} not available",
                        tool_call_id=tool_call['id']
                    )
                    messages.append(error_message)
            
            # Get final response from model after tool execution
            final_prompt = self.prompt_template.invoke({"messages": messages})
            final_response = self.model_with_tools.invoke(final_prompt)
            
            # Store AI response in database if memory service is available
            if self.memory_service:
                # Extract token usage information from response
                token_usage = None
                if hasattr(final_response, 'response_metadata') and final_response.response_metadata:
                    usage_metadata = final_response.response_metadata.get('usage_metadata', {})
                    if usage_metadata:
                        token_usage = {
                            'input_tokens': usage_metadata.get('input_tokens'),
                            'output_tokens': usage_metadata.get('output_tokens'),
                            'total_tokens': usage_metadata.get('total_tokens'),
                            'model_name': final_response.response_metadata.get('model_name', 'gemini-2.5-flash')
                        }
                
                self.memory_service.add_message('ai', final_response.content, token_usage=token_usage)
            
            return {"messages": [final_response]}
        
        # Store AI response in database if memory service is available (no tools case)
        if self.memory_service:
            # Extract token usage information from response
            token_usage = None
            if hasattr(response, 'response_metadata') and response.response_metadata:
                usage_metadata = response.response_metadata.get('usage_metadata', {})
                if usage_metadata:
                    token_usage = {
                        'input_tokens': usage_metadata.get('input_tokens'),
                        'output_tokens': usage_metadata.get('output_tokens'),
                        'total_tokens': usage_metadata.get('total_tokens'),
                        'model_name': response.response_metadata.get('model_name', 'gemini-2.5-flash')
                    }
            
            self.memory_service.add_message('ai', response.content, token_usage=token_usage)
        
        return {"messages": [response]}

    def get_prompt_template(self) -> ChatPromptTemplate:
        logger.info("Getting prompt template")
        print(self.system_prompt)
        
        # Add memory tool instructions if tools are available
        memory_instructions = ""
        if self.memory_tools:
            memory_instructions = """

MEMORY TOOLS AVAILABLE:
You have access to memory search tools to find information from previous conversations:

1. search_memory(query, limit=10): Search through previous conversation history to find relevant information. Use this when:
   - User asks about something that might have been discussed before
   - You need more context about a topic
   - User refers to previous conversations or events
   - You need to recall specific details from past interactions

2. get_conversation_summary(): Get a summary of the current conversation thread including message counts and dates.

IMPORTANT: Always use search_memory when the user mentions something that might not be in your current context (last 5 messages). This helps you provide more accurate and contextual responses.

Example usage:
- User: "What did I tell you about my project yesterday?" → Use search_memory("project yesterday")
- User: "Remember when we discussed the meeting?" → Use search_memory("meeting discussion")
- User: "Can you summarize our conversation?" → Use get_conversation_summary()

"""

        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    self.system_prompt + memory_instructions + "\n" + text_formatting_guide
                ),
                MessagesPlaceholder(variable_name="messages")
            ]
        )
    
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
    
    def cleanup_memory(self, keep_recent: int = 100) -> int:
        """
        Clean up old messages from memory.
        
        Args:
            keep_recent: Number of recent messages to keep
            
        Returns:
            Number of messages cleaned up
        """
        if self.memory_service:
            return self.memory_service.cleanup_old_messages(keep_recent)
        return 0
    
    def get_conversation_summary(self) -> dict:
        """
        Get a summary of the conversation.
        
        Returns:
            Dictionary with conversation statistics
        """
        if self.memory_service:
            return self.memory_service.get_conversation_summary()
        return {}
    
    def update_embeddings(self) -> int:
        """
        Update embeddings for messages that don't have them.
        
        Returns:
            Number of messages updated
        """
        if self.memory_service:
            return self.memory_service.update_message_embeddings()
        return 0
    
    def search_knowledge_base(self, query: str, top_k: int = 3) -> list:
        """
        Search the user's knowledge base for relevant information.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of relevant knowledge base chunks
        """
        if not self.knowledge_base_service:
            logger.warning("Knowledge base service not available")
            return []
        
        try:
            # Get user from memory service if available
            user = None
            if self.memory_service and hasattr(self.memory_service, 'thread'):
                user = self.memory_service.thread.user
            
            if not user:
                logger.warning("User not available for knowledge base search")
                return []
            
            results = self.knowledge_base_service.search_knowledge_base(user, query, top_k)
            logger.info(f"Found {len(results)} knowledge base results for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def get_knowledge_base_context(self, query: str, max_chunks: int = 3, min_similarity: float = 0.7) -> str:
        """
        Get relevant knowledge base context for a query with filtering.
        
        Args:
            query: Search query
            max_chunks: Maximum number of chunks to include
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            
        Returns:
            Formatted knowledge base context string
        """
        results = self.search_knowledge_base(query, max_chunks)
        
        if not results:
            return ""
        
        # Filter results by similarity threshold
        filtered_results = []
        for result in results:
            similarity_score = getattr(result, 'similarity_score', 0.0)
            if similarity_score >= min_similarity:
                filtered_results.append(result)
        
        if not filtered_results:
            logger.info(f"No knowledge base results above similarity threshold {min_similarity}")
            return ""
        
        context_parts = []
        for i, result in enumerate(filtered_results, 1):
            similarity_score = getattr(result, 'similarity_score', 0.0)
            context_parts.append(
                f"Knowledge Base Reference {i} (from {result.original_filename}, similarity: {similarity_score:.2f}):\n"
                f"{result.chunk_text}\n"
            )
        
        logger.info(f"Added {len(filtered_results)} knowledge base chunks to context")
        return "\n".join(context_parts)
    
    def _should_search_knowledge_base(self, query: str) -> bool:
        """
        Determine if the knowledge base should be searched for this query.
        
        Args:
            query: User query
            
        Returns:
            True if knowledge base search should be performed
        """
        # Skip very short queries
        if len(query.strip()) < 10:
            return False
        
        # Skip simple greetings and commands
        skip_patterns = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
            'thank you', 'thanks', 'bye', 'goodbye', 'see you',
            'help', 'what can you do', 'who are you'
        ]
        
        query_lower = query.lower().strip()
        for pattern in skip_patterns:
            if pattern in query_lower:
                return False
        
        # Skip queries that are just punctuation or very short
        if len(query.strip()) < 10 or query.strip() in ['?', '!', '.', ',']:
            return False
        
        return True
    
if __name__ == '__main__':
    assistant = ChatAssistant("user001")
    query = input("Enter your message: ")
    print(assistant.send_message(query).content)