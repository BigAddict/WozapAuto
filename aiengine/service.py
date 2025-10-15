from langgraph.graph import START, MessagesState, StateGraph, add_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, trim_messages
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import init_chat_model

from aiengine.prompts import text_formatting_guide
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
    def __init__(self, thread_id: str, system_instructions: str):
        self.thread_id = thread_id
        self.system_prompt = system_instructions
        self.model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
        self.config = {"configurable": {"thread_id": thread_id}}
        self.memory = MemorySaver()
        self.prompt_template = self.get_prompt_template()
        self.init_workflow()
        self.trimmer = self.message_trimmer()

    def init_workflow(self):
        logger.info("Initializing workflow")
        self.workflow = StateGraph(state_schema=State)
        self.workflow.add_edge(START, "model")
        self.workflow.add_node("model", self.call_model)
        self.app = self.workflow.compile(checkpointer=self.memory)

    def send_message(self, message: str) -> AIMessage:
        logger.info(f"Sending message: {message}")
        input_messages = [HumanMessage(message)]
        output = self.app.invoke({"messages": input_messages}, self.config)
        return output["messages"][-1]

    def call_model(self, state: State):
        logger.info(f"Calling model with state: {state}")
        state["messages"] = self.trimmer.invoke(state['messages'])
        prompt = self.prompt_template.invoke(state)
        response = self.model.invoke(prompt)
        return {"messages": response}

    def get_prompt_template(self) -> ChatPromptTemplate:
        logger.info("Getting prompt template")
        # Clean the system prompt to remove any template variables that might cause issues
        clean_system_prompt = self.system_prompt.replace('{', '{{').replace('}', '}}')
        
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"{clean_system_prompt}\n{text_formatting_guide}"
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
    
if __name__ == '__main__':
    assistant = ChatAssistant("user001")
    query = input("Enter your message: ")
    print(assistant.send_message(query).content)