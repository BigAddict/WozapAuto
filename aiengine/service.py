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
from typing_extensions import Annotated, TypedDict
from typing import Sequence, Optional
from dotenv import load_dotenv
import logging
import os

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
            except Exception as e:
                logger.error(f"Error initializing database-backed memory: {e}")
                # Fallback to in-memory storage
                from langgraph.checkpoint.memory import MemorySaver
                self.checkpointer = MemorySaver()
                self.memory_service = None
                self.memory_tools = None
        else:
            # Fallback to in-memory storage for backward compatibility
            from langgraph.checkpoint.memory import MemorySaver
            self.checkpointer = MemorySaver()
            self.memory_service = None
            self.memory_tools = None
        
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
        
        # Store human message in database if memory service is available
        if self.memory_service:
            self.memory_service.add_message('human', message)
        
        input_messages = [HumanMessage(message)]
        output = self.app.invoke({"messages": input_messages}, self.config)
        ai_response = output["messages"][-1]
        
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
        
        # Trim messages to fit context window
        state["messages"] = self.trimmer.invoke(state['messages'])
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
        
        # Trim messages to fit context window
        state["messages"] = self.trimmer.invoke(state['messages'])
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
            max_tokens: int = 65,
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
    
if __name__ == '__main__':
    assistant = ChatAssistant("user001")
    query = input("Enter your message: ")
    print(assistant.send_message(query).content)