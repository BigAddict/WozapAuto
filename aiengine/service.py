from langgraph.graph import START, MessagesState, StateGraph, add_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, trim_messages
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model

from aiengine.prompts import text_formatting_guide
from aiengine.checkpointer import DatabaseCheckpointSaver
from aiengine.memory_service import MemoryService
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
            except Exception as e:
                logger.error(f"Error initializing database-backed memory: {e}")
                # Fallback to in-memory storage
                from langgraph.checkpoint.memory import MemorySaver
                self.checkpointer = MemorySaver()
                self.memory_service = None
        else:
            # Fallback to in-memory storage for backward compatibility
            from langgraph.checkpoint.memory import MemorySaver
            self.checkpointer = MemorySaver()
            self.memory_service = None
        
        self.prompt_template = self.get_prompt_template()
        self.init_workflow()
        self.trimmer = self.message_trimmer()

    def init_workflow(self):
        logger.info("Initializing workflow")
        self.workflow = StateGraph(state_schema=State)
        self.workflow.add_edge(START, "model")
        self.workflow.add_node("model", self.call_model)
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
            self.memory_service.add_message('ai', ai_response.content)
        
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
            
            if latest_human_message:
                # Get relevant context messages
                context_messages = self.memory_service.get_context_messages(
                    query=latest_human_message,
                    max_messages=15  # Limit context to prevent token overflow
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

    def get_prompt_template(self) -> ChatPromptTemplate:
        logger.info("Getting prompt template")
        print(self.system_prompt)
        
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    self.system_prompt + "\n" + text_formatting_guide
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