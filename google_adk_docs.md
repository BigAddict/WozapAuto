We'll embark on building a Weather Bot agent team, progressively layering advanced features onto a simple foundation. Starting with a single agent that can look up weather, we will incrementally add capabilities like:

Leveraging different AI models (Gemini, GPT, Claude).
Designing specialized sub-agents for distinct tasks (like greetings and farewells).
Enabling intelligent delegation between agents.
Giving agents memory using persistent session state.
Implementing crucial safety guardrails using callbacks.
Why a Weather Bot Team?

This use case, while seemingly simple, provides a practical and relatable canvas to explore core ADK concepts essential for building complex, real-world agentic applications. You'll learn how to structure interactions, manage state, ensure safety, and orchestrate multiple AI "brains" working together.

What is ADK Again?

As a reminder, ADK is a Python framework designed to streamline the development of applications powered by Large Language Models (LLMs). It offers robust building blocks for creating agents that can reason, plan, utilize tools, interact dynamically with users, and collaborate effectively within a team.

In this advanced tutorial, you will master:

✅ Tool Definition & Usage: Crafting Python functions (tools) that grant agents specific abilities (like fetching data) and instructing agents on how to use them effectively.
✅ Multi-LLM Flexibility: Configuring agents to utilize various leading LLMs (Gemini, GPT-4o, Claude Sonnet) via LiteLLM integration, allowing you to choose the best model for each task.
✅ Agent Delegation & Collaboration: Designing specialized sub-agents and enabling automatic routing (auto flow) of user requests to the most appropriate agent within a team.
✅ Session State for Memory: Utilizing Session State and ToolContext to enable agents to remember information across conversational turns, leading to more contextual interactions.
✅ Safety Guardrails with Callbacks: Implementing before_model_callback and before_tool_callback to inspect, modify, or block requests/tool usage based on predefined rules, enhancing application safety and control.
End State Expectation:

By completing this tutorial, you will have built a functional multi-agent Weather Bot system. This system will not only provide weather information but also handle conversational niceties, remember the last city checked, and operate within defined safety boundaries, all orchestrated using ADK.

Prerequisites:

✅ Solid understanding of Python programming.
✅ Familiarity with Large Language Models (LLMs), APIs, and the concept of agents.
❗ Crucially: Completion of the ADK Quickstart tutorial(s) or equivalent foundational knowledge of ADK basics (Agent, Runner, SessionService, basic Tool usage). This tutorial builds directly upon those concepts.
✅ API Keys for the LLMs you intend to use (e.g., Google AI Studio for Gemini, OpenAI Platform, Anthropic Console).
Note on Execution Environment:

This tutorial is structured for interactive notebook environments like Google Colab, Colab Enterprise, or Jupyter notebooks. Please keep the following in mind:

Running Async Code: Notebook environments handle asynchronous code differently. You'll see examples using await (suitable when an event loop is already running, common in notebooks) or asyncio.run() (often needed when running as a standalone .py script or in specific notebook setups). The code blocks provide guidance for both scenarios.
Manual Runner/Session Setup: The steps involve explicitly creating Runner and SessionService instances. This approach is shown because it gives you fine-grained control over the agent's execution lifecycle, session management, and state persistence.
Alternative: Using ADK's Built-in Tools (Web UI / CLI / API Server)

If you prefer a setup that handles the runner and session management automatically using ADK's standard tools, you can find the equivalent code structured for that purpose here. That version is designed to be run directly with commands like adk web (for a web UI), adk run (for CLI interaction), or adk api_server (to expose an API). Please follow the README.md instructions provided in that alternative resource.

Ready to build your agent team? Let's dive in!

Note: This tutorial works with adk version 1.0.0 and above


# @title Step 0: Setup and Installation
# Install ADK and LiteLLM for multi-model support

!pip install google-adk -q
!pip install litellm -q

print("Installation complete.")

# @title Import necessary libraries
import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts

import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")

import logging
logging.basicConfig(level=logging.ERROR)

print("Libraries imported.")

# @title Configure API Keys (Replace with your actual keys!)

# --- IMPORTANT: Replace placeholders with your real API keys ---

# Gemini API Key (Get from Google AI Studio: https://aistudio.google.com/app/apikey)
os.environ["GOOGLE_API_KEY"] = "YOUR_GOOGLE_API_KEY" # <--- REPLACE

# [Optional]
# OpenAI API Key (Get from OpenAI Platform: https://platform.openai.com/api-keys)
os.environ['OPENAI_API_KEY'] = 'YOUR_OPENAI_API_KEY' # <--- REPLACE

# [Optional]
# Anthropic API Key (Get from Anthropic Console: https://console.anthropic.com/settings/keys)
os.environ['ANTHROPIC_API_KEY'] = 'YOUR_ANTHROPIC_API_KEY' # <--- REPLACE

# --- Verify Keys (Optional Check) ---
print("API Keys Set:")
print(f"Google API Key set: {'Yes' if os.environ.get('GOOGLE_API_KEY') and os.environ['GOOGLE_API_KEY'] != 'YOUR_GOOGLE_API_KEY' else 'No (REPLACE PLACEHOLDER!)'}")
print(f"OpenAI API Key set: {'Yes' if os.environ.get('OPENAI_API_KEY') and os.environ['OPENAI_API_KEY'] != 'YOUR_OPENAI_API_KEY' else 'No (REPLACE PLACEHOLDER!)'}")
print(f"Anthropic API Key set: {'Yes' if os.environ.get('ANTHROPIC_API_KEY') and os.environ['ANTHROPIC_API_KEY'] != 'YOUR_ANTHROPIC_API_KEY' else 'No (REPLACE PLACEHOLDER!)'}")

# Configure ADK to use API keys directly (not Vertex AI for this multi-model setup)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"


# @markdown **Security Note:** It's best practice to manage API keys securely (e.g., using Colab Secrets or environment variables) rather than hardcoding them directly in the notebook. Replace the placeholder strings above.

# --- Define Model Constants for easier use ---

# More supported models can be referenced here: https://ai.google.dev/gemini-api/docs/models#model-variations
MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"

# More supported models can be referenced here: https://docs.litellm.ai/docs/providers/openai#openai-chat-completion-models
MODEL_GPT_4O = "openai/gpt-4.1" # You can also try: gpt-4.1-mini, gpt-4o etc.

# More supported models can be referenced here: https://docs.litellm.ai/docs/providers/anthropic
MODEL_CLAUDE_SONNET = "anthropic/claude-sonnet-4-20250514" # You can also try: claude-opus-4-20250514 , claude-3-7-sonnet-20250219 etc

print("\nEnvironment configured.")
Step 1: Your First Agent - Basic Weather Lookup¶
Let's begin by building the fundamental component of our Weather Bot: a single agent capable of performing a specific task – looking up weather information. This involves creating two core pieces:

A Tool: A Python function that equips the agent with the ability to fetch weather data.
An Agent: The AI "brain" that understands the user's request, knows it has a weather tool, and decides when and how to use it.
1. Define the Tool (get_weather)

In ADK, Tools are the building blocks that give agents concrete capabilities beyond just text generation. They are typically regular Python functions that perform specific actions, like calling an API, querying a database, or performing calculations.

Our first tool will provide a mock weather report. This allows us to focus on the agent structure without needing external API keys yet. Later, you could easily swap this mock function with one that calls a real weather service.

Key Concept: Docstrings are Crucial! The agent's LLM relies heavily on the function's docstring to understand:

What the tool does.
When to use it.
What arguments it requires (city: str).
What information it returns.
Best Practice: Write clear, descriptive, and accurate docstrings for your tools. This is essential for the LLM to use the tool correctly.


# @title Define the get_weather Tool
def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city (e.g., "New York", "London", "Tokyo").

    Returns:
        dict: A dictionary containing the weather information.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'report' key with weather details.
              If 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather called for city: {city} ---") # Log tool execution
    city_normalized = city.lower().replace(" ", "") # Basic normalization

    # Mock weather data
    mock_weather_db = {
        "newyork": {"status": "success", "report": "The weather in New York is sunny with a temperature of 25°C."},
        "london": {"status": "success", "report": "It's cloudy in London with a temperature of 15°C."},
        "tokyo": {"status": "success", "report": "Tokyo is experiencing light rain and a temperature of 18°C."},
    }

    if city_normalized in mock_weather_db:
        return mock_weather_db[city_normalized]
    else:
        return {"status": "error", "error_message": f"Sorry, I don't have weather information for '{city}'."}

# Example tool usage (optional test)
print(get_weather("New York"))
print(get_weather("Paris"))
2. Define the Agent (weather_agent)

Now, let's create the Agent itself. An Agent in ADK orchestrates the interaction between the user, the LLM, and the available tools.

We configure it with several key parameters:

name: A unique identifier for this agent (e.g., "weather_agent_v1").
model: Specifies which LLM to use (e.g., MODEL_GEMINI_2_0_FLASH). We'll start with a specific Gemini model.
description: A concise summary of the agent's overall purpose. This becomes crucial later when other agents need to decide whether to delegate tasks to this agent.
instruction: Detailed guidance for the LLM on how to behave, its persona, its goals, and specifically how and when to utilize its assigned tools.
tools: A list containing the actual Python tool functions the agent is allowed to use (e.g., [get_weather]).
Best Practice: Provide clear and specific instruction prompts. The more detailed the instructions, the better the LLM can understand its role and how to use its tools effectively. Be explicit about error handling if needed.

Best Practice: Choose descriptive name and description values. These are used internally by ADK and are vital for features like automatic delegation (covered later).


# @title Define the Weather Agent
# Use one of the model constants defined earlier
AGENT_MODEL = MODEL_GEMINI_2_0_FLASH # Starting with Gemini

weather_agent = Agent(
    name="weather_agent_v1",
    model=AGENT_MODEL, # Can be a string for Gemini or a LiteLlm object
    description="Provides weather information for specific cities.",
    instruction="You are a helpful weather assistant. "
                "When the user asks for the weather in a specific city, "
                "use the 'get_weather' tool to find the information. "
                "If the tool returns an error, inform the user politely. "
                "If the tool is successful, present the weather report clearly.",
    tools=[get_weather], # Pass the function directly
)

print(f"Agent '{weather_agent.name}' created using model '{AGENT_MODEL}'.")
3. Setup Runner and Session Service

To manage conversations and execute the agent, we need two more components:

SessionService: Responsible for managing conversation history and state for different users and sessions. The InMemorySessionService is a simple implementation that stores everything in memory, suitable for testing and simple applications. It keeps track of the messages exchanged. We'll explore state persistence more in Step 4.
Runner: The engine that orchestrates the interaction flow. It takes user input, routes it to the appropriate agent, manages calls to the LLM and tools based on the agent's logic, handles session updates via the SessionService, and yields events representing the progress of the interaction.

# @title Setup Session Service and Runner

# --- Session Management ---
# Key Concept: SessionService stores conversation history & state.
# InMemorySessionService is simple, non-persistent storage for this tutorial.
session_service = InMemorySessionService()

# Define constants for identifying the interaction context
APP_NAME = "weather_tutorial_app"
USER_ID = "user_1"
SESSION_ID = "session_001" # Using a fixed ID for simplicity

# Create the specific session where the conversation will happen
session = await session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
)
print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

# --- Runner ---
# Key Concept: Runner orchestrates the agent execution loop.
runner = Runner(
    agent=weather_agent, # The agent we want to run
    app_name=APP_NAME,   # Associates runs with our app
    session_service=session_service # Uses our session manager
)
print(f"Runner created for agent '{runner.agent.name}'.")
4. Interact with the Agent

We need a way to send messages to our agent and receive its responses. Since LLM calls and tool executions can take time, ADK's Runner operates asynchronously.

We'll define an async helper function (call_agent_async) that:

Takes a user query string.
Packages it into the ADK Content format.
Calls runner.run_async, providing the user/session context and the new message.
Iterates through the Events yielded by the runner. Events represent steps in the agent's execution (e.g., tool call requested, tool result received, intermediate LLM thought, final response).
Identifies and prints the final response event using event.is_final_response().
Why async? Interactions with LLMs and potentially tools (like external APIs) are I/O-bound operations. Using asyncio allows the program to handle these operations efficiently without blocking execution.


# @title Define Agent Interaction Function

from google.genai import types # For creating message Content/Parts

async def call_agent_async(query: str, runner, user_id, session_id):
  """Sends a query to the agent and prints the final response."""
  print(f"\n>>> User Query: {query}")

  # Prepare the user's message in ADK format
  content = types.Content(role='user', parts=[types.Part(text=query)])

  final_response_text = "Agent did not produce a final response." # Default

  # Key Concept: run_async executes the agent logic and yields Events.
  # We iterate through events to find the final answer.
  async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
      # You can uncomment the line below to see *all* events during execution
      # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

      # Key Concept: is_final_response() marks the concluding message for the turn.
      if event.is_final_response():
          if event.content and event.content.parts:
             # Assuming text response in the first part
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate: # Handle potential errors/escalations
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          # Add more checks here if needed (e.g., specific error codes)
          break # Stop processing events once the final response is found

  print(f"<<< Agent Response: {final_response_text}")
5. Run the Conversation

Finally, let's test our setup by sending a few queries to the agent. We wrap our async calls in a main async function and run it using await.

Watch the output:

See the user queries.
Notice the --- Tool: get_weather called... --- logs when the agent uses the tool.
Observe the agent's final responses, including how it handles the case where weather data isn't available (for Paris).

# @title Run the Initial Conversation

# We need an async function to await our interaction helper
async def run_conversation():
    await call_agent_async("What is the weather like in London?",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID)

    await call_agent_async("How about Paris?",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID) # Expecting the tool's error message

    await call_agent_async("Tell me the weather in New York",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID)

# Execute the conversation using await in an async context (like Colab/Jupyter)
await run_conversation()

# --- OR ---

# Uncomment the following lines if running as a standard Python script (.py file):
# import asyncio
# if __name__ == "__main__":
#     try:
#         asyncio.run(run_conversation())
#     except Exception as e:
#         print(f"An error occurred: {e}")
Congratulations! You've successfully built and interacted with your first ADK agent. It understands the user's request, uses a tool to find information, and responds appropriately based on the tool's result.

In the next step, we'll explore how to easily switch the underlying Language Model powering this agent.

Step 2: Going Multi-Model with LiteLLM [Optional]¶
In Step 1, we built a functional Weather Agent powered by a specific Gemini model. While effective, real-world applications often benefit from the flexibility to use different Large Language Models (LLMs). Why?

Performance: Some models excel at specific tasks (e.g., coding, reasoning, creative writing).
Cost: Different models have varying price points.
Capabilities: Models offer diverse features, context window sizes, and fine-tuning options.
Availability/Redundancy: Having alternatives ensures your application remains functional even if one provider experiences issues.
ADK makes switching between models seamless through its integration with the LiteLLM library. LiteLLM acts as a consistent interface to over 100 different LLMs.

In this step, we will:

Learn how to configure an ADK Agent to use models from providers like OpenAI (GPT) and Anthropic (Claude) using the LiteLlm wrapper.
Define, configure (with their own sessions and runners), and immediately test instances of our Weather Agent, each backed by a different LLM.
Interact with these different agents to observe potential variations in their responses, even when using the same underlying tool.
1. Import LiteLlm

We imported this during the initial setup (Step 0), but it's the key component for multi-model support:


# @title 1. Import LiteLlm
from google.adk.models.lite_llm import LiteLlm
2. Define and Test Multi-Model Agents

Instead of passing only a model name string (which defaults to Google's Gemini models), we wrap the desired model identifier string within the LiteLlm class.

Key Concept: LiteLlm Wrapper: The LiteLlm(model="provider/model_name") syntax tells ADK to route requests for this agent through the LiteLLM library to the specified model provider.
Make sure you have configured the necessary API keys for OpenAI and Anthropic in Step 0. We'll use the call_agent_async function (defined earlier, which now accepts runner, user_id, and session_id) to interact with each agent immediately after its setup.

Each block below will:

Define the agent using a specific LiteLLM model (MODEL_GPT_4O or MODEL_CLAUDE_SONNET).
Create a new, separate InMemorySessionService and session specifically for that agent's test run. This keeps the conversation histories isolated for this demonstration.
Create a Runner configured for the specific agent and its session service.
Immediately call call_agent_async to send a query and test the agent.
Best Practice: Use constants for model names (like MODEL_GPT_4O, MODEL_CLAUDE_SONNET defined in Step 0) to avoid typos and make code easier to manage.

Error Handling: We wrap the agent definitions in try...except blocks. This prevents the entire code cell from failing if an API key for a specific provider is missing or invalid, allowing the tutorial to proceed with the models that are configured.

First, let's create and test the agent using OpenAI's GPT-4o.


# @title Define and Test GPT Agent

# Make sure 'get_weather' function from Step 1 is defined in your environment.
# Make sure 'call_agent_async' is defined from earlier.

# --- Agent using GPT-4o ---
weather_agent_gpt = None # Initialize to None
runner_gpt = None      # Initialize runner to None

try:
    weather_agent_gpt = Agent(
        name="weather_agent_gpt",
        # Key change: Wrap the LiteLLM model identifier
        model=LiteLlm(model=MODEL_GPT_4O),
        description="Provides weather information (using GPT-4o).",
        instruction="You are a helpful weather assistant powered by GPT-4o. "
                    "Use the 'get_weather' tool for city weather requests. "
                    "Clearly present successful reports or polite error messages based on the tool's output status.",
        tools=[get_weather], # Re-use the same tool
    )
    print(f"Agent '{weather_agent_gpt.name}' created using model '{MODEL_GPT_4O}'.")

    # InMemorySessionService is simple, non-persistent storage for this tutorial.
    session_service_gpt = InMemorySessionService() # Create a dedicated service

    # Define constants for identifying the interaction context
    APP_NAME_GPT = "weather_tutorial_app_gpt" # Unique app name for this test
    USER_ID_GPT = "user_1_gpt"
    SESSION_ID_GPT = "session_001_gpt" # Using a fixed ID for simplicity

    # Create the specific session where the conversation will happen
    session_gpt = await session_service_gpt.create_session(
        app_name=APP_NAME_GPT,
        user_id=USER_ID_GPT,
        session_id=SESSION_ID_GPT
    )
    print(f"Session created: App='{APP_NAME_GPT}', User='{USER_ID_GPT}', Session='{SESSION_ID_GPT}'")

    # Create a runner specific to this agent and its session service
    runner_gpt = Runner(
        agent=weather_agent_gpt,
        app_name=APP_NAME_GPT,       # Use the specific app name
        session_service=session_service_gpt # Use the specific session service
        )
    print(f"Runner created for agent '{runner_gpt.agent.name}'.")

    # --- Test the GPT Agent ---
    print("\n--- Testing GPT Agent ---")
    # Ensure call_agent_async uses the correct runner, user_id, session_id
    await call_agent_async(query = "What's the weather in Tokyo?",
                           runner=runner_gpt,
                           user_id=USER_ID_GPT,
                           session_id=SESSION_ID_GPT)
    # --- OR ---

    # Uncomment the following lines if running as a standard Python script (.py file):
    # import asyncio
    # if __name__ == "__main__":
    #     try:
    #         asyncio.run(call_agent_async(query = "What's the weather in Tokyo?",
    #                      runner=runner_gpt,
    #                       user_id=USER_ID_GPT,
    #                       session_id=SESSION_ID_GPT)
    #     except Exception as e:
    #         print(f"An error occurred: {e}")

except Exception as e:
    print(f"❌ Could not create or run GPT agent '{MODEL_GPT_4O}'. Check API Key and model name. Error: {e}")
Next, we'll do the same for Anthropic's Claude Sonnet.


# @title Define and Test Claude Agent

# Make sure 'get_weather' function from Step 1 is defined in your environment.
# Make sure 'call_agent_async' is defined from earlier.

# --- Agent using Claude Sonnet ---
weather_agent_claude = None # Initialize to None
runner_claude = None      # Initialize runner to None

try:
    weather_agent_claude = Agent(
        name="weather_agent_claude",
        # Key change: Wrap the LiteLLM model identifier
        model=LiteLlm(model=MODEL_CLAUDE_SONNET),
        description="Provides weather information (using Claude Sonnet).",
        instruction="You are a helpful weather assistant powered by Claude Sonnet. "
                    "Use the 'get_weather' tool for city weather requests. "
                    "Analyze the tool's dictionary output ('status', 'report'/'error_message'). "
                    "Clearly present successful reports or polite error messages.",
        tools=[get_weather], # Re-use the same tool
    )
    print(f"Agent '{weather_agent_claude.name}' created using model '{MODEL_CLAUDE_SONNET}'.")

    # InMemorySessionService is simple, non-persistent storage for this tutorial.
    session_service_claude = InMemorySessionService() # Create a dedicated service

    # Define constants for identifying the interaction context
    APP_NAME_CLAUDE = "weather_tutorial_app_claude" # Unique app name
    USER_ID_CLAUDE = "user_1_claude"
    SESSION_ID_CLAUDE = "session_001_claude" # Using a fixed ID for simplicity

    # Create the specific session where the conversation will happen
    session_claude = await session_service_claude.create_session(
        app_name=APP_NAME_CLAUDE,
        user_id=USER_ID_CLAUDE,
        session_id=SESSION_ID_CLAUDE
    )
    print(f"Session created: App='{APP_NAME_CLAUDE}', User='{USER_ID_CLAUDE}', Session='{SESSION_ID_CLAUDE}'")

    # Create a runner specific to this agent and its session service
    runner_claude = Runner(
        agent=weather_agent_claude,
        app_name=APP_NAME_CLAUDE,       # Use the specific app name
        session_service=session_service_claude # Use the specific session service
        )
    print(f"Runner created for agent '{runner_claude.agent.name}'.")

    # --- Test the Claude Agent ---
    print("\n--- Testing Claude Agent ---")
    # Ensure call_agent_async uses the correct runner, user_id, session_id
    await call_agent_async(query = "Weather in London please.",
                           runner=runner_claude,
                           user_id=USER_ID_CLAUDE,
                           session_id=SESSION_ID_CLAUDE)

    # --- OR ---

    # Uncomment the following lines if running as a standard Python script (.py file):
    # import asyncio
    # if __name__ == "__main__":
    #     try:
    #         asyncio.run(call_agent_async(query = "Weather in London please.",
    #                      runner=runner_claude,
    #                       user_id=USER_ID_CLAUDE,
    #                       session_id=SESSION_ID_CLAUDE)
    #     except Exception as e:
    #         print(f"An error occurred: {e}")


except Exception as e:
    print(f"❌ Could not create or run Claude agent '{MODEL_CLAUDE_SONNET}'. Check API Key and model name. Error: {e}")
Observe the output carefully from both code blocks. You should see:

Each agent (weather_agent_gpt, weather_agent_claude) is created successfully (if API keys are valid).
A dedicated session and runner are set up for each.
Each agent correctly identifies the need to use the get_weather tool when processing the query (you'll see the --- Tool: get_weather called... --- log).
The underlying tool logic remains identical, always returning our mock data.
However, the final textual response generated by each agent might differ slightly in phrasing, tone, or formatting. This is because the instruction prompt is interpreted and executed by different LLMs (GPT-4o vs. Claude Sonnet).
This step demonstrates the power and flexibility ADK + LiteLLM provide. You can easily experiment with and deploy agents using various LLMs while keeping your core application logic (tools, fundamental agent structure) consistent.

In the next step, we'll move beyond a single agent and build a small team where agents can delegate tasks to each other!

Step 3: Building an Agent Team - Delegation for Greetings & Farewells¶
In Steps 1 and 2, we built and experimented with a single agent focused solely on weather lookups. While effective for its specific task, real-world applications often involve handling a wider variety of user interactions. We could keep adding more tools and complex instructions to our single weather agent, but this can quickly become unmanageable and less efficient.

A more robust approach is to build an Agent Team. This involves:

Creating multiple, specialized agents, each designed for a specific capability (e.g., one for weather, one for greetings, one for calculations).
Designating a root agent (or orchestrator) that receives the initial user request.
Enabling the root agent to delegate the request to the most appropriate specialized sub-agent based on the user's intent.
Why build an Agent Team?

Modularity: Easier to develop, test, and maintain individual agents.
Specialization: Each agent can be fine-tuned (instructions, model choice) for its specific task.
Scalability: Simpler to add new capabilities by adding new agents.
Efficiency: Allows using potentially simpler/cheaper models for simpler tasks (like greetings).
In this step, we will:

Define simple tools for handling greetings (say_hello) and farewells (say_goodbye).
Create two new specialized sub-agents: greeting_agent and farewell_agent.
Update our main weather agent (weather_agent_v2) to act as the root agent.
Configure the root agent with its sub-agents, enabling automatic delegation.
Test the delegation flow by sending different types of requests to the root agent.
1. Define Tools for Sub-Agents

First, let's create the simple Python functions that will serve as tools for our new specialist agents. Remember, clear docstrings are vital for the agents that will use them.


# @title Define Tools for Greeting and Farewell Agents
from typing import Optional # Make sure to import Optional

# Ensure 'get_weather' from Step 1 is available if running this step independently.
# def get_weather(city: str) -> dict: ... (from Step 1)

def say_hello(name: Optional[str] = None) -> str:
    """Provides a simple greeting. If a name is provided, it will be used.

    Args:
        name (str, optional): The name of the person to greet. Defaults to a generic greeting if not provided.

    Returns:
        str: A friendly greeting message.
    """
    if name:
        greeting = f"Hello, {name}!"
        print(f"--- Tool: say_hello called with name: {name} ---")
    else:
        greeting = "Hello there!" # Default greeting if name is None or not explicitly passed
        print(f"--- Tool: say_hello called without a specific name (name_arg_value: {name}) ---")
    return greeting

def say_goodbye() -> str:
    """Provides a simple farewell message to conclude the conversation."""
    print(f"--- Tool: say_goodbye called ---")
    return "Goodbye! Have a great day."

print("Greeting and Farewell tools defined.")

# Optional self-test
print(say_hello("Alice"))
print(say_hello()) # Test with no argument (should use default "Hello there!")
print(say_hello(name=None)) # Test with name explicitly as None (should use default "Hello there!")
2. Define the Sub-Agents (Greeting & Farewell)

Now, create the Agent instances for our specialists. Notice their highly focused instruction and, critically, their clear description. The description is the primary information the root agent uses to decide when to delegate to these sub-agents.

Best Practice: Sub-agent description fields should accurately and concisely summarize their specific capability. This is crucial for effective automatic delegation.

Best Practice: Sub-agent instruction fields should be tailored to their limited scope, telling them exactly what to do and what not to do (e.g., "Your only task is...").


# @title Define Greeting and Farewell Sub-Agents

# If you want to use models other than Gemini, Ensure LiteLlm is imported and API keys are set (from Step 0/2)
# from google.adk.models.lite_llm import LiteLlm
# MODEL_GPT_4O, MODEL_CLAUDE_SONNET etc. should be defined
# Or else, continue to use: model = MODEL_GEMINI_2_0_FLASH

# --- Greeting Agent ---
greeting_agent = None
try:
    greeting_agent = Agent(
        # Using a potentially different/cheaper model for a simple task
        model = MODEL_GEMINI_2_0_FLASH,
        # model=LiteLlm(model=MODEL_GPT_4O), # If you would like to experiment with other models
        name="greeting_agent",
        instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting to the user. "
                    "Use the 'say_hello' tool to generate the greeting. "
                    "If the user provides their name, make sure to pass it to the tool. "
                    "Do not engage in any other conversation or tasks.",
        description="Handles simple greetings and hellos using the 'say_hello' tool.", # Crucial for delegation
        tools=[say_hello],
    )
    print(f"✅ Agent '{greeting_agent.name}' created using model '{greeting_agent.model}'.")
except Exception as e:
    print(f"❌ Could not create Greeting agent. Check API Key ({greeting_agent.model}). Error: {e}")

# --- Farewell Agent ---
farewell_agent = None
try:
    farewell_agent = Agent(
        # Can use the same or a different model
        model = MODEL_GEMINI_2_0_FLASH,
        # model=LiteLlm(model=MODEL_GPT_4O), # If you would like to experiment with other models
        name="farewell_agent",
        instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message. "
                    "Use the 'say_goodbye' tool when the user indicates they are leaving or ending the conversation "
                    "(e.g., using words like 'bye', 'goodbye', 'thanks bye', 'see you'). "
                    "Do not perform any other actions.",
        description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.", # Crucial for delegation
        tools=[say_goodbye],
    )
    print(f"✅ Agent '{farewell_agent.name}' created using model '{farewell_agent.model}'.")
except Exception as e:
    print(f"❌ Could not create Farewell agent. Check API Key ({farewell_agent.model}). Error: {e}")
3. Define the Root Agent (Weather Agent v2) with Sub-Agents

Now, we upgrade our weather_agent. The key changes are:

Adding the sub_agents parameter: We pass a list containing the greeting_agent and farewell_agent instances we just created.
Updating the instruction: We explicitly tell the root agent about its sub-agents and when it should delegate tasks to them.
Key Concept: Automatic Delegation (Auto Flow) By providing the sub_agents list, ADK enables automatic delegation. When the root agent receives a user query, its LLM considers not only its own instructions and tools but also the description of each sub-agent. If the LLM determines that a query aligns better with a sub-agent's described capability (e.g., "Handles simple greetings"), it will automatically generate a special internal action to transfer control to that sub-agent for that turn. The sub-agent then processes the query using its own model, instructions, and tools.

Best Practice: Ensure the root agent's instructions clearly guide its delegation decisions. Mention the sub-agents by name and describe the conditions under which delegation should occur.


# @title Define the Root Agent with Sub-Agents

# Ensure sub-agents were created successfully before defining the root agent.
# Also ensure the original 'get_weather' tool is defined.
root_agent = None
runner_root = None # Initialize runner

if greeting_agent and farewell_agent and 'get_weather' in globals():
    # Let's use a capable Gemini model for the root agent to handle orchestration
    root_agent_model = MODEL_GEMINI_2_0_FLASH

    weather_agent_team = Agent(
        name="weather_agent_v2", # Give it a new version name
        model=root_agent_model,
        description="The main coordinator agent. Handles weather requests and delegates greetings/farewells to specialists.",
        instruction="You are the main Weather Agent coordinating a team. Your primary responsibility is to provide weather information. "
                    "Use the 'get_weather' tool ONLY for specific weather requests (e.g., 'weather in London'). "
                    "You have specialized sub-agents: "
                    "1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. "
                    "2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. "
                    "Analyze the user's query. If it's a greeting, delegate to 'greeting_agent'. If it's a farewell, delegate to 'farewell_agent'. "
                    "If it's a weather request, handle it yourself using 'get_weather'. "
                    "For anything else, respond appropriately or state you cannot handle it.",
        tools=[get_weather], # Root agent still needs the weather tool for its core task
        # Key change: Link the sub-agents here!
        sub_agents=[greeting_agent, farewell_agent]
    )
    print(f"✅ Root Agent '{weather_agent_team.name}' created using model '{root_agent_model}' with sub-agents: {[sa.name for sa in weather_agent_team.sub_agents]}")

else:
    print("❌ Cannot create root agent because one or more sub-agents failed to initialize or 'get_weather' tool is missing.")
    if not greeting_agent: print(" - Greeting Agent is missing.")
    if not farewell_agent: print(" - Farewell Agent is missing.")
    if 'get_weather' not in globals(): print(" - get_weather function is missing.")
4. Interact with the Agent Team

Now that we've defined our root agent (weather_agent_team - Note: Ensure this variable name matches the one defined in the previous code block, likely # @title Define the Root Agent with Sub-Agents, which might have named it root_agent) with its specialized sub-agents, let's test the delegation mechanism.

The following code block will:

Define an async function run_team_conversation.
Inside this function, create a new, dedicated InMemorySessionService and a specific session (session_001_agent_team) just for this test run. This isolates the conversation history for testing the team dynamics.
Create a Runner (runner_agent_team) configured to use our weather_agent_team (the root agent) and the dedicated session service.
Use our updated call_agent_async function to send different types of queries (greeting, weather request, farewell) to the runner_agent_team. We explicitly pass the runner, user ID, and session ID for this specific test.
Immediately execute the run_team_conversation function.
We expect the following flow:

The "Hello there!" query goes to runner_agent_team.
The root agent (weather_agent_team) receives it and, based on its instructions and the greeting_agent's description, delegates the task.
greeting_agent handles the query, calls its say_hello tool, and generates the response.
The "What is the weather in New York?" query is not delegated and is handled directly by the root agent using its get_weather tool.
The "Thanks, bye!" query is delegated to the farewell_agent, which uses its say_goodbye tool.

# @title Interact with the Agent Team
import asyncio # Ensure asyncio is imported

# Ensure the root agent (e.g., 'weather_agent_team' or 'root_agent' from the previous cell) is defined.
# Ensure the call_agent_async function is defined.

# Check if the root agent variable exists before defining the conversation function
root_agent_var_name = 'root_agent' # Default name from Step 3 guide
if 'weather_agent_team' in globals(): # Check if user used this name instead
    root_agent_var_name = 'weather_agent_team'
elif 'root_agent' not in globals():
    print("⚠️ Root agent ('root_agent' or 'weather_agent_team') not found. Cannot define run_team_conversation.")
    # Assign a dummy value to prevent NameError later if the code block runs anyway
    root_agent = None # Or set a flag to prevent execution

# Only define and run if the root agent exists
if root_agent_var_name in globals() and globals()[root_agent_var_name]:
    # Define the main async function for the conversation logic.
    # The 'await' keywords INSIDE this function are necessary for async operations.
    async def run_team_conversation():
        print("\n--- Testing Agent Team Delegation ---")
        session_service = InMemorySessionService()
        APP_NAME = "weather_tutorial_agent_team"
        USER_ID = "user_1_agent_team"
        SESSION_ID = "session_001_agent_team"
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
        print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

        actual_root_agent = globals()[root_agent_var_name]
        runner_agent_team = Runner( # Or use InMemoryRunner
            agent=actual_root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        print(f"Runner created for agent '{actual_root_agent.name}'.")

        # --- Interactions using await (correct within async def) ---
        await call_agent_async(query = "Hello there!",
                               runner=runner_agent_team,
                               user_id=USER_ID,
                               session_id=SESSION_ID)
        await call_agent_async(query = "What is the weather in New York?",
                               runner=runner_agent_team,
                               user_id=USER_ID,
                               session_id=SESSION_ID)
        await call_agent_async(query = "Thanks, bye!",
                               runner=runner_agent_team,
                               user_id=USER_ID,
                               session_id=SESSION_ID)

    # --- Execute the `run_team_conversation` async function ---
    # Choose ONE of the methods below based on your environment.
    # Note: This may require API keys for the models used!

    # METHOD 1: Direct await (Default for Notebooks/Async REPLs)
    # If your environment supports top-level await (like Colab/Jupyter notebooks),
    # it means an event loop is already running, so you can directly await the function.
    print("Attempting execution using 'await' (default for notebooks)...")
    await run_team_conversation()

    # METHOD 2: asyncio.run (For Standard Python Scripts [.py])
    # If running this code as a standard Python script from your terminal,
    # the script context is synchronous. `asyncio.run()` is needed to
    # create and manage an event loop to execute your async function.
    # To use this method:
    # 1. Comment out the `await run_team_conversation()` line above.
    # 2. Uncomment the following block:
    """
    import asyncio
    if __name__ == "__main__": # Ensures this runs only when script is executed directly
        print("Executing using 'asyncio.run()' (for standard Python scripts)...")
        try:
            # This creates an event loop, runs your async function, and closes the loop.
            asyncio.run(run_team_conversation())
        except Exception as e:
            print(f"An error occurred: {e}")
    """

else:
    # This message prints if the root agent variable wasn't found earlier
    print("\n⚠️ Skipping agent team conversation execution as the root agent was not successfully defined in a previous step.")
Look closely at the output logs, especially the --- Tool: ... called --- messages. You should observe:

For "Hello there!", the say_hello tool was called (indicating greeting_agent handled it).
For "What is the weather in New York?", the get_weather tool was called (indicating the root agent handled it).
For "Thanks, bye!", the say_goodbye tool was called (indicating farewell_agent handled it).
This confirms successful automatic delegation! The root agent, guided by its instructions and the descriptions of its sub_agents, correctly routed user requests to the appropriate specialist agent within the team.

You've now structured your application with multiple collaborating agents. This modular design is fundamental for building more complex and capable agent systems. In the next step, we'll give our agents the ability to remember information across turns using session state.

Step 4: Adding Memory and Personalization with Session State¶
So far, our agent team can handle different tasks through delegation, but each interaction starts fresh – the agents have no memory of past conversations or user preferences within a session. To create more sophisticated and context-aware experiences, agents need memory. ADK provides this through Session State.

What is Session State?

It's a Python dictionary (session.state) tied to a specific user session (identified by APP_NAME, USER_ID, SESSION_ID).
It persists information across multiple conversational turns within that session.
Agents and Tools can read from and write to this state, allowing them to remember details, adapt behavior, and personalize responses.
How Agents Interact with State:

ToolContext (Primary Method): Tools can accept a ToolContext object (automatically provided by ADK if declared as the last argument). This object gives direct access to the session state via tool_context.state, allowing tools to read preferences or save results during execution.
output_key (Auto-Save Agent Response): An Agent can be configured with an output_key="your_key". ADK will then automatically save the agent's final textual response for a turn into session.state["your_key"].
In this step, we will enhance our Weather Bot team by:

Using a new InMemorySessionService to demonstrate state in isolation.
Initializing session state with a user preference for temperature_unit.
Creating a state-aware version of the weather tool (get_weather_stateful) that reads this preference via ToolContext and adjusts its output format (Celsius/Fahrenheit).
Updating the root agent to use this stateful tool and configuring it with an output_key to automatically save its final weather report to the session state.
Running a conversation to observe how the initial state affects the tool, how manual state changes alter subsequent behavior, and how output_key persists the agent's response.
1. Initialize New Session Service and State

To clearly demonstrate state management without interference from prior steps, we'll instantiate a new InMemorySessionService. We'll also create a session with an initial state defining the user's preferred temperature unit.


# @title 1. Initialize New Session Service and State

# Import necessary session components
from google.adk.sessions import InMemorySessionService

# Create a NEW session service instance for this state demonstration
session_service_stateful = InMemorySessionService()
print("✅ New InMemorySessionService created for state demonstration.")

# Define a NEW session ID for this part of the tutorial
SESSION_ID_STATEFUL = "session_state_demo_001"
USER_ID_STATEFUL = "user_state_demo"

# Define initial state data - user prefers Celsius initially
initial_state = {
    "user_preference_temperature_unit": "Celsius"
}

# Create the session, providing the initial state
session_stateful = await session_service_stateful.create_session(
    app_name=APP_NAME, # Use the consistent app name
    user_id=USER_ID_STATEFUL,
    session_id=SESSION_ID_STATEFUL,
    state=initial_state # <<< Initialize state during creation
)
print(f"✅ Session '{SESSION_ID_STATEFUL}' created for user '{USER_ID_STATEFUL}'.")

# Verify the initial state was set correctly
retrieved_session = await session_service_stateful.get_session(app_name=APP_NAME,
                                                         user_id=USER_ID_STATEFUL,
                                                         session_id = SESSION_ID_STATEFUL)
print("\n--- Initial Session State ---")
if retrieved_session:
    print(retrieved_session.state)
else:
    print("Error: Could not retrieve session.")
2. Create State-Aware Weather Tool (get_weather_stateful)

Now, we create a new version of the weather tool. Its key feature is accepting tool_context: ToolContext which allows it to access tool_context.state. It will read the user_preference_temperature_unit and format the temperature accordingly.

Key Concept: ToolContext This object is the bridge allowing your tool logic to interact with the session's context, including reading and writing state variables. ADK injects it automatically if defined as the last parameter of your tool function.

Best Practice: When reading from state, use dictionary.get('key', default_value) to handle cases where the key might not exist yet, ensuring your tool doesn't crash.


from google.adk.tools.tool_context import ToolContext

def get_weather_stateful(city: str, tool_context: ToolContext) -> dict:
    """Retrieves weather, converts temp unit based on session state."""
    print(f"--- Tool: get_weather_stateful called for {city} ---")

    # --- Read preference from state ---
    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "Celsius") # Default to Celsius
    print(f"--- Tool: Reading state 'user_preference_temperature_unit': {preferred_unit} ---")

    city_normalized = city.lower().replace(" ", "")

    # Mock weather data (always stored in Celsius internally)
    mock_weather_db = {
        "newyork": {"temp_c": 25, "condition": "sunny"},
        "london": {"temp_c": 15, "condition": "cloudy"},
        "tokyo": {"temp_c": 18, "condition": "light rain"},
    }

    if city_normalized in mock_weather_db:
        data = mock_weather_db[city_normalized]
        temp_c = data["temp_c"]
        condition = data["condition"]

        # Format temperature based on state preference
        if preferred_unit == "Fahrenheit":
            temp_value = (temp_c * 9/5) + 32 # Calculate Fahrenheit
            temp_unit = "°F"
        else: # Default to Celsius
            temp_value = temp_c
            temp_unit = "°C"

        report = f"The weather in {city.capitalize()} is {condition} with a temperature of {temp_value:.0f}{temp_unit}."
        result = {"status": "success", "report": report}
        print(f"--- Tool: Generated report in {preferred_unit}. Result: {result} ---")

        # Example of writing back to state (optional for this tool)
        tool_context.state["last_city_checked_stateful"] = city
        print(f"--- Tool: Updated state 'last_city_checked_stateful': {city} ---")

        return result
    else:
        # Handle city not found
        error_msg = f"Sorry, I don't have weather information for '{city}'."
        print(f"--- Tool: City '{city}' not found. ---")
        return {"status": "error", "error_message": error_msg}

print("✅ State-aware 'get_weather_stateful' tool defined.")
3. Redefine Sub-Agents and Update Root Agent

To ensure this step is self-contained and builds correctly, we first redefine the greeting_agent and farewell_agent exactly as they were in Step 3. Then, we define our new root agent (weather_agent_v4_stateful):

It uses the new get_weather_stateful tool.
It includes the greeting and farewell sub-agents for delegation.
Crucially, it sets output_key="last_weather_report" which automatically saves its final weather response to the session state.

# @title 3. Redefine Sub-Agents and Update Root Agent with output_key

# Ensure necessary imports: Agent, LiteLlm, Runner
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
# Ensure tools 'say_hello', 'say_goodbye' are defined (from Step 3)
# Ensure model constants MODEL_GPT_4O, MODEL_GEMINI_2_0_FLASH etc. are defined

# --- Redefine Greeting Agent (from Step 3) ---
greeting_agent = None
try:
    greeting_agent = Agent(
        model=MODEL_GEMINI_2_0_FLASH,
        name="greeting_agent",
        instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting using the 'say_hello' tool. Do nothing else.",
        description="Handles simple greetings and hellos using the 'say_hello' tool.",
        tools=[say_hello],
    )
    print(f"✅ Agent '{greeting_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Greeting agent. Error: {e}")

# --- Redefine Farewell Agent (from Step 3) ---
farewell_agent = None
try:
    farewell_agent = Agent(
        model=MODEL_GEMINI_2_0_FLASH,
        name="farewell_agent",
        instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message using the 'say_goodbye' tool. Do not perform any other actions.",
        description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
        tools=[say_goodbye],
    )
    print(f"✅ Agent '{farewell_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Farewell agent. Error: {e}")

# --- Define the Updated Root Agent ---
root_agent_stateful = None
runner_root_stateful = None # Initialize runner

# Check prerequisites before creating the root agent
if greeting_agent and farewell_agent and 'get_weather_stateful' in globals():

    root_agent_model = MODEL_GEMINI_2_0_FLASH # Choose orchestration model

    root_agent_stateful = Agent(
        name="weather_agent_v4_stateful", # New version name
        model=root_agent_model,
        description="Main agent: Provides weather (state-aware unit), delegates greetings/farewells, saves report to state.",
        instruction="You are the main Weather Agent. Your job is to provide weather using 'get_weather_stateful'. "
                    "The tool will format the temperature based on user preference stored in state. "
                    "Delegate simple greetings to 'greeting_agent' and farewells to 'farewell_agent'. "
                    "Handle only weather requests, greetings, and farewells.",
        tools=[get_weather_stateful], # Use the state-aware tool
        sub_agents=[greeting_agent, farewell_agent], # Include sub-agents
        output_key="last_weather_report" # <<< Auto-save agent's final weather response
    )
    print(f"✅ Root Agent '{root_agent_stateful.name}' created using stateful tool and output_key.")

    # --- Create Runner for this Root Agent & NEW Session Service ---
    runner_root_stateful = Runner(
        agent=root_agent_stateful,
        app_name=APP_NAME,
        session_service=session_service_stateful # Use the NEW stateful session service
    )
    print(f"✅ Runner created for stateful root agent '{runner_root_stateful.agent.name}' using stateful session service.")

else:
    print("❌ Cannot create stateful root agent. Prerequisites missing.")
    if not greeting_agent: print(" - greeting_agent definition missing.")
    if not farewell_agent: print(" - farewell_agent definition missing.")
    if 'get_weather_stateful' not in globals(): print(" - get_weather_stateful tool missing.")
4. Interact and Test State Flow

Now, let's execute a conversation designed to test the state interactions using the runner_root_stateful (associated with our stateful agent and the session_service_stateful). We'll use the call_agent_async function defined earlier, ensuring we pass the correct runner, user ID (USER_ID_STATEFUL), and session ID (SESSION_ID_STATEFUL).

The conversation flow will be:

Check weather (London): The get_weather_stateful tool should read the initial "Celsius" preference from the session state initialized in Section 1. The root agent's final response (the weather report in Celsius) should get saved to state['last_weather_report'] via the output_key configuration.
Manually update state: We will directly modify the state stored within the InMemorySessionService instance (session_service_stateful).
Why direct modification? The session_service.get_session() method returns a copy of the session. Modifying that copy wouldn't affect the state used in subsequent agent runs. For this testing scenario with InMemorySessionService, we access the internal sessions dictionary to change the actual stored state value for user_preference_temperature_unit to "Fahrenheit". Note: In real applications, state changes are typically triggered by tools or agent logic returning EventActions(state_delta=...), not direct manual updates.
Check weather again (New York): The get_weather_stateful tool should now read the updated "Fahrenheit" preference from the state and convert the temperature accordingly. The root agent's new response (weather in Fahrenheit) will overwrite the previous value in state['last_weather_report'] due to the output_key.
Greet the agent: Verify that delegation to the greeting_agent still works correctly alongside the stateful operations. This interaction will become the last response saved by output_key in this specific sequence.
Inspect final state: After the conversation, we retrieve the session one last time (getting a copy) and print its state to confirm the user_preference_temperature_unit is indeed "Fahrenheit", observe the final value saved by output_key (which will be the greeting in this run), and see the last_city_checked_stateful value written by the tool.

# @title 4. Interact to Test State Flow and output_key
import asyncio # Ensure asyncio is imported

# Ensure the stateful runner (runner_root_stateful) is available from the previous cell
# Ensure call_agent_async, USER_ID_STATEFUL, SESSION_ID_STATEFUL, APP_NAME are defined

if 'runner_root_stateful' in globals() and runner_root_stateful:
    # Define the main async function for the stateful conversation logic.
    # The 'await' keywords INSIDE this function are necessary for async operations.
    async def run_stateful_conversation():
        print("\n--- Testing State: Temp Unit Conversion & output_key ---")

        # 1. Check weather (Uses initial state: Celsius)
        print("--- Turn 1: Requesting weather in London (expect Celsius) ---")
        await call_agent_async(query= "What's the weather in London?",
                               runner=runner_root_stateful,
                               user_id=USER_ID_STATEFUL,
                               session_id=SESSION_ID_STATEFUL
                              )

        # 2. Manually update state preference to Fahrenheit - DIRECTLY MODIFY STORAGE
        print("\n--- Manually Updating State: Setting unit to Fahrenheit ---")
        try:
            # Access the internal storage directly - THIS IS SPECIFIC TO InMemorySessionService for testing
            # NOTE: In production with persistent services (Database, VertexAI), you would
            # typically update state via agent actions or specific service APIs if available,
            # not by direct manipulation of internal storage.
            stored_session = session_service_stateful.sessions[APP_NAME][USER_ID_STATEFUL][SESSION_ID_STATEFUL]
            stored_session.state["user_preference_temperature_unit"] = "Fahrenheit"
            # Optional: You might want to update the timestamp as well if any logic depends on it
            # import time
            # stored_session.last_update_time = time.time()
            print(f"--- Stored session state updated. Current 'user_preference_temperature_unit': {stored_session.state.get('user_preference_temperature_unit', 'Not Set')} ---") # Added .get for safety
        except KeyError:
            print(f"--- Error: Could not retrieve session '{SESSION_ID_STATEFUL}' from internal storage for user '{USER_ID_STATEFUL}' in app '{APP_NAME}' to update state. Check IDs and if session was created. ---")
        except Exception as e:
             print(f"--- Error updating internal session state: {e} ---")

        # 3. Check weather again (Tool should now use Fahrenheit)
        # This will also update 'last_weather_report' via output_key
        print("\n--- Turn 2: Requesting weather in New York (expect Fahrenheit) ---")
        await call_agent_async(query= "Tell me the weather in New York.",
                               runner=runner_root_stateful,
                               user_id=USER_ID_STATEFUL,
                               session_id=SESSION_ID_STATEFUL
                              )

        # 4. Test basic delegation (should still work)
        # This will update 'last_weather_report' again, overwriting the NY weather report
        print("\n--- Turn 3: Sending a greeting ---")
        await call_agent_async(query= "Hi!",
                               runner=runner_root_stateful,
                               user_id=USER_ID_STATEFUL,
                               session_id=SESSION_ID_STATEFUL
                              )

    # --- Execute the `run_stateful_conversation` async function ---
    # Choose ONE of the methods below based on your environment.

    # METHOD 1: Direct await (Default for Notebooks/Async REPLs)
    # If your environment supports top-level await (like Colab/Jupyter notebooks),
    # it means an event loop is already running, so you can directly await the function.
    print("Attempting execution using 'await' (default for notebooks)...")
    await run_stateful_conversation()

    # METHOD 2: asyncio.run (For Standard Python Scripts [.py])
    # If running this code as a standard Python script from your terminal,
    # the script context is synchronous. `asyncio.run()` is needed to
    # create and manage an event loop to execute your async function.
    # To use this method:
    # 1. Comment out the `await run_stateful_conversation()` line above.
    # 2. Uncomment the following block:
    """
    import asyncio
    if __name__ == "__main__": # Ensures this runs only when script is executed directly
        print("Executing using 'asyncio.run()' (for standard Python scripts)...")
        try:
            # This creates an event loop, runs your async function, and closes the loop.
            asyncio.run(run_stateful_conversation())
        except Exception as e:
            print(f"An error occurred: {e}")
    """

    # --- Inspect final session state after the conversation ---
    # This block runs after either execution method completes.
    print("\n--- Inspecting Final Session State ---")
    final_session = await session_service_stateful.get_session(app_name=APP_NAME,
                                                         user_id= USER_ID_STATEFUL,
                                                         session_id=SESSION_ID_STATEFUL)
    if final_session:
        # Use .get() for safer access to potentially missing keys
        print(f"Final Preference: {final_session.state.get('user_preference_temperature_unit', 'Not Set')}")
        print(f"Final Last Weather Report (from output_key): {final_session.state.get('last_weather_report', 'Not Set')}")
        print(f"Final Last City Checked (by tool): {final_session.state.get('last_city_checked_stateful', 'Not Set')}")
        # Print full state for detailed view
        # print(f"Full State Dict: {final_session.state}") # For detailed view
    else:
        print("\n❌ Error: Could not retrieve final session state.")

else:
    print("\n⚠️ Skipping state test conversation. Stateful root agent runner ('runner_root_stateful') is not available.")
By reviewing the conversation flow and the final session state printout, you can confirm:

State Read: The weather tool (get_weather_stateful) correctly read user_preference_temperature_unit from state, initially using "Celsius" for London.
State Update: The direct modification successfully changed the stored preference to "Fahrenheit".
State Read (Updated): The tool subsequently read "Fahrenheit" when asked for New York's weather and performed the conversion.
Tool State Write: The tool successfully wrote the last_city_checked_stateful ("New York" after the second weather check) into the state via tool_context.state.
Delegation: The delegation to the greeting_agent for "Hi!" functioned correctly even after state modifications.
output_key: The output_key="last_weather_report" successfully saved the root agent's final response for each turn where the root agent was the one ultimately responding. In this sequence, the last response was the greeting ("Hello, there!"), so that overwrote the weather report in the state key.
Final State: The final check confirms the preference persisted as "Fahrenheit".
You've now successfully integrated session state to personalize agent behavior using ToolContext, manually manipulated state for testing InMemorySessionService, and observed how output_key provides a simple mechanism for saving the agent's last response to state. This foundational understanding of state management is key as we proceed to implement safety guardrails using callbacks in the next steps.

Step 5: Adding Safety - Input Guardrail with before_model_callback¶
Our agent team is becoming more capable, remembering preferences and using tools effectively. However, in real-world scenarios, we often need safety mechanisms to control the agent's behavior before potentially problematic requests even reach the core Large Language Model (LLM).

ADK provides Callbacks – functions that allow you to hook into specific points in the agent's execution lifecycle. The before_model_callback is particularly useful for input safety.

What is before_model_callback?

It's a Python function you define that ADK executes just before an agent sends its compiled request (including conversation history, instructions, and the latest user message) to the underlying LLM.
Purpose: Inspect the request, modify it if necessary, or block it entirely based on predefined rules.
Common Use Cases:

Input Validation/Filtering: Check if user input meets criteria or contains disallowed content (like PII or keywords).
Guardrails: Prevent harmful, off-topic, or policy-violating requests from being processed by the LLM.
Dynamic Prompt Modification: Add timely information (e.g., from session state) to the LLM request context just before sending.
How it Works:

Define a function accepting callback_context: CallbackContext and llm_request: LlmRequest.

callback_context: Provides access to agent info, session state (callback_context.state), etc.
llm_request: Contains the full payload intended for the LLM (contents, config).
Inside the function:

Inspect: Examine llm_request.contents (especially the last user message).
Modify (Use Caution): You can change parts of llm_request.
Block (Guardrail): Return an LlmResponse object. ADK will send this response back immediately, skipping the LLM call for that turn.
Allow: Return None. ADK proceeds to call the LLM with the (potentially modified) request.
In this step, we will:

Define a before_model_callback function (block_keyword_guardrail) that checks the user's input for a specific keyword ("BLOCK").
Update our stateful root agent (weather_agent_v4_stateful from Step 4) to use this callback.
Create a new runner associated with this updated agent but using the same stateful session service to maintain state continuity.
Test the guardrail by sending both normal and keyword-containing requests.
1. Define the Guardrail Callback Function

This function will inspect the last user message within the llm_request content. If it finds "BLOCK" (case-insensitive), it constructs and returns an LlmResponse to block the flow; otherwise, it returns None.


# @title 1. Define the before_model_callback Guardrail

# Ensure necessary imports are available
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types # For creating response content
from typing import Optional

def block_keyword_guardrail(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Inspects the latest user message for 'BLOCK'. If found, blocks the LLM call
    and returns a predefined LlmResponse. Otherwise, returns None to proceed.
    """
    agent_name = callback_context.agent_name # Get the name of the agent whose model call is being intercepted
    print(f"--- Callback: block_keyword_guardrail running for agent: {agent_name} ---")

    # Extract the text from the latest user message in the request history
    last_user_message_text = ""
    if llm_request.contents:
        # Find the most recent message with role 'user'
        for content in reversed(llm_request.contents):
            if content.role == 'user' and content.parts:
                # Assuming text is in the first part for simplicity
                if content.parts[0].text:
                    last_user_message_text = content.parts[0].text
                    break # Found the last user message text

    print(f"--- Callback: Inspecting last user message: '{last_user_message_text[:100]}...' ---") # Log first 100 chars

    # --- Guardrail Logic ---
    keyword_to_block = "BLOCK"
    if keyword_to_block in last_user_message_text.upper(): # Case-insensitive check
        print(f"--- Callback: Found '{keyword_to_block}'. Blocking LLM call! ---")
        # Optionally, set a flag in state to record the block event
        callback_context.state["guardrail_block_keyword_triggered"] = True
        print(f"--- Callback: Set state 'guardrail_block_keyword_triggered': True ---")

        # Construct and return an LlmResponse to stop the flow and send this back instead
        return LlmResponse(
            content=types.Content(
                role="model", # Mimic a response from the agent's perspective
                parts=[types.Part(text=f"I cannot process this request because it contains the blocked keyword '{keyword_to_block}'.")],
            )
            # Note: You could also set an error_message field here if needed
        )
    else:
        # Keyword not found, allow the request to proceed to the LLM
        print(f"--- Callback: Keyword not found. Allowing LLM call for {agent_name}. ---")
        return None # Returning None signals ADK to continue normally

print("✅ block_keyword_guardrail function defined.")
2. Update Root Agent to Use the Callback

We redefine the root agent, adding the before_model_callback parameter and pointing it to our new guardrail function. We'll give it a new version name for clarity.

Important: We need to redefine the sub-agents (greeting_agent, farewell_agent) and the stateful tool (get_weather_stateful) within this context if they are not already available from previous steps, ensuring the root agent definition has access to all its components.


# @title 2. Update Root Agent with before_model_callback


# --- Redefine Sub-Agents (Ensures they exist in this context) ---
greeting_agent = None
try:
    # Use a defined model constant
    greeting_agent = Agent(
        model=MODEL_GEMINI_2_0_FLASH,
        name="greeting_agent", # Keep original name for consistency
        instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting using the 'say_hello' tool. Do nothing else.",
        description="Handles simple greetings and hellos using the 'say_hello' tool.",
        tools=[say_hello],
    )
    print(f"✅ Sub-Agent '{greeting_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Greeting agent. Check Model/API Key ({greeting_agent.model}). Error: {e}")

farewell_agent = None
try:
    # Use a defined model constant
    farewell_agent = Agent(
        model=MODEL_GEMINI_2_0_FLASH,
        name="farewell_agent", # Keep original name
        instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message using the 'say_goodbye' tool. Do not perform any other actions.",
        description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
        tools=[say_goodbye],
    )
    print(f"✅ Sub-Agent '{farewell_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Farewell agent. Check Model/API Key ({farewell_agent.model}). Error: {e}")


# --- Define the Root Agent with the Callback ---
root_agent_model_guardrail = None
runner_root_model_guardrail = None

# Check all components before proceeding
if greeting_agent and farewell_agent and 'get_weather_stateful' in globals() and 'block_keyword_guardrail' in globals():

    # Use a defined model constant
    root_agent_model = MODEL_GEMINI_2_0_FLASH

    root_agent_model_guardrail = Agent(
        name="weather_agent_v5_model_guardrail", # New version name for clarity
        model=root_agent_model,
        description="Main agent: Handles weather, delegates greetings/farewells, includes input keyword guardrail.",
        instruction="You are the main Weather Agent. Provide weather using 'get_weather_stateful'. "
                    "Delegate simple greetings to 'greeting_agent' and farewells to 'farewell_agent'. "
                    "Handle only weather requests, greetings, and farewells.",
        tools=[get_weather_stateful],
        sub_agents=[greeting_agent, farewell_agent], # Reference the redefined sub-agents
        output_key="last_weather_report", # Keep output_key from Step 4
        before_model_callback=block_keyword_guardrail # <<< Assign the guardrail callback
    )
    print(f"✅ Root Agent '{root_agent_model_guardrail.name}' created with before_model_callback.")

    # --- Create Runner for this Agent, Using SAME Stateful Session Service ---
    # Ensure session_service_stateful exists from Step 4
    if 'session_service_stateful' in globals():
        runner_root_model_guardrail = Runner(
            agent=root_agent_model_guardrail,
            app_name=APP_NAME, # Use consistent APP_NAME
            session_service=session_service_stateful # <<< Use the service from Step 4
        )
        print(f"✅ Runner created for guardrail agent '{runner_root_model_guardrail.agent.name}', using stateful session service.")
    else:
        print("❌ Cannot create runner. 'session_service_stateful' from Step 4 is missing.")

else:
    print("❌ Cannot create root agent with model guardrail. One or more prerequisites are missing or failed initialization:")
    if not greeting_agent: print("   - Greeting Agent")
    if not farewell_agent: print("   - Farewell Agent")
    if 'get_weather_stateful' not in globals(): print("   - 'get_weather_stateful' tool")
    if 'block_keyword_guardrail' not in globals(): print("   - 'block_keyword_guardrail' callback")
3. Interact to Test the Guardrail

Let's test the guardrail's behavior. We'll use the same session (SESSION_ID_STATEFUL) as in Step 4 to show that state persists across these changes.

Send a normal weather request (should pass the guardrail and execute).
Send a request containing "BLOCK" (should be intercepted by the callback).
Send a greeting (should pass the root agent's guardrail, be delegated, and execute normally).

# @title 3. Interact to Test the Model Input Guardrail
import asyncio # Ensure asyncio is imported

# Ensure the runner for the guardrail agent is available
if 'runner_root_model_guardrail' in globals() and runner_root_model_guardrail:
    # Define the main async function for the guardrail test conversation.
    # The 'await' keywords INSIDE this function are necessary for async operations.
    async def run_guardrail_test_conversation():
        print("\n--- Testing Model Input Guardrail ---")

        # Use the runner for the agent with the callback and the existing stateful session ID
        # Define a helper lambda for cleaner interaction calls
        interaction_func = lambda query: call_agent_async(query,
                                                         runner_root_model_guardrail,
                                                         USER_ID_STATEFUL, # Use existing user ID
                                                         SESSION_ID_STATEFUL # Use existing session ID
                                                        )
        # 1. Normal request (Callback allows, should use Fahrenheit from previous state change)
        print("--- Turn 1: Requesting weather in London (expect allowed, Fahrenheit) ---")
        await interaction_func("What is the weather in London?")

        # 2. Request containing the blocked keyword (Callback intercepts)
        print("\n--- Turn 2: Requesting with blocked keyword (expect blocked) ---")
        await interaction_func("BLOCK the request for weather in Tokyo") # Callback should catch "BLOCK"

        # 3. Normal greeting (Callback allows root agent, delegation happens)
        print("\n--- Turn 3: Sending a greeting (expect allowed) ---")
        await interaction_func("Hello again")

    # --- Execute the `run_guardrail_test_conversation` async function ---
    # Choose ONE of the methods below based on your environment.

    # METHOD 1: Direct await (Default for Notebooks/Async REPLs)
    # If your environment supports top-level await (like Colab/Jupyter notebooks),
    # it means an event loop is already running, so you can directly await the function.
    print("Attempting execution using 'await' (default for notebooks)...")
    await run_guardrail_test_conversation()

    # METHOD 2: asyncio.run (For Standard Python Scripts [.py])
    # If running this code as a standard Python script from your terminal,
    # the script context is synchronous. `asyncio.run()` is needed to
    # create and manage an event loop to execute your async function.
    # To use this method:
    # 1. Comment out the `await run_guardrail_test_conversation()` line above.
    # 2. Uncomment the following block:
    """
    import asyncio
    if __name__ == "__main__": # Ensures this runs only when script is executed directly
        print("Executing using 'asyncio.run()' (for standard Python scripts)...")
        try:
            # This creates an event loop, runs your async function, and closes the loop.
            asyncio.run(run_guardrail_test_conversation())
        except Exception as e:
            print(f"An error occurred: {e}")
    """

    # --- Inspect final session state after the conversation ---
    # This block runs after either execution method completes.
    # Optional: Check state for the trigger flag set by the callback
    print("\n--- Inspecting Final Session State (After Guardrail Test) ---")
    # Use the session service instance associated with this stateful session
    final_session = await session_service_stateful.get_session(app_name=APP_NAME,
                                                         user_id=USER_ID_STATEFUL,
                                                         session_id=SESSION_ID_STATEFUL)
    if final_session:
        # Use .get() for safer access
        print(f"Guardrail Triggered Flag: {final_session.state.get('guardrail_block_keyword_triggered', 'Not Set (or False)')}")
        print(f"Last Weather Report: {final_session.state.get('last_weather_report', 'Not Set')}") # Should be London weather if successful
        print(f"Temperature Unit: {final_session.state.get('user_preference_temperature_unit', 'Not Set')}") # Should be Fahrenheit
        # print(f"Full State Dict: {final_session.state}") # For detailed view
    else:
        print("\n❌ Error: Could not retrieve final session state.")

else:
    print("\n⚠️ Skipping model guardrail test. Runner ('runner_root_model_guardrail') is not available.")
Observe the execution flow:

London Weather: The callback runs for weather_agent_v5_model_guardrail, inspects the message, prints "Keyword not found. Allowing LLM call.", and returns None. The agent proceeds, calls the get_weather_stateful tool (which uses the "Fahrenheit" preference from Step 4's state change), and returns the weather. This response updates last_weather_report via output_key.
BLOCK Request: The callback runs again for weather_agent_v5_model_guardrail, inspects the message, finds "BLOCK", prints "Blocking LLM call!", sets the state flag, and returns the predefined LlmResponse. The agent's underlying LLM is never called for this turn. The user sees the callback's blocking message.
Hello Again: The callback runs for weather_agent_v5_model_guardrail, allows the request. The root agent then delegates to greeting_agent. Note: The before_model_callback defined on the root agent does NOT automatically apply to sub-agents. The greeting_agent proceeds normally, calls its say_hello tool, and returns the greeting.
You have successfully implemented an input safety layer! The before_model_callback provides a powerful mechanism to enforce rules and control agent behavior before expensive or potentially risky LLM calls are made. Next, we'll apply a similar concept to add guardrails around tool usage itself.

Step 6: Adding Safety - Tool Argument Guardrail (before_tool_callback)¶
In Step 5, we added a guardrail to inspect and potentially block user input before it reached the LLM. Now, we'll add another layer of control after the LLM has decided to use a tool but before that tool actually executes. This is useful for validating the arguments the LLM wants to pass to the tool.

ADK provides the before_tool_callback for this precise purpose.

What is before_tool_callback?

It's a Python function executed just before a specific tool function runs, after the LLM has requested its use and decided on the arguments.
Purpose: Validate tool arguments, prevent tool execution based on specific inputs, modify arguments dynamically, or enforce resource usage policies.
Common Use Cases:

Argument Validation: Check if arguments provided by the LLM are valid, within allowed ranges, or conform to expected formats.
Resource Protection: Prevent tools from being called with inputs that might be costly, access restricted data, or cause unwanted side effects (e.g., blocking API calls for certain parameters).
Dynamic Argument Modification: Adjust arguments based on session state or other contextual information before the tool runs.
How it Works:

Define a function accepting tool: BaseTool, args: Dict[str, Any], and tool_context: ToolContext.

tool: The tool object about to be called (inspect tool.name).
args: The dictionary of arguments the LLM generated for the tool.
tool_context: Provides access to session state (tool_context.state), agent info, etc.
Inside the function:

Inspect: Examine the tool.name and the args dictionary.
Modify: Change values within the args dictionary directly. If you return None, the tool runs with these modified args.
Block/Override (Guardrail): Return a dictionary. ADK treats this dictionary as the result of the tool call, completely skipping the execution of the original tool function. The dictionary should ideally match the expected return format of the tool it's blocking.
Allow: Return None. ADK proceeds to execute the actual tool function with the (potentially modified) arguments.
In this step, we will:

Define a before_tool_callback function (block_paris_tool_guardrail) that specifically checks if the get_weather_stateful tool is called with the city "Paris".
If "Paris" is detected, the callback will block the tool and return a custom error dictionary.
Update our root agent (weather_agent_v6_tool_guardrail) to include both the before_model_callback and this new before_tool_callback.
Create a new runner for this agent, using the same stateful session service.
Test the flow by requesting weather for allowed cities and the blocked city ("Paris").
1. Define the Tool Guardrail Callback Function

This function targets the get_weather_stateful tool. It checks the city argument. If it's "Paris", it returns an error dictionary that looks like the tool's own error response. Otherwise, it allows the tool to run by returning None.


# @title 1. Define the before_tool_callback Guardrail

# Ensure necessary imports are available
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from typing import Optional, Dict, Any # For type hints

def block_paris_tool_guardrail(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """
    Checks if 'get_weather_stateful' is called for 'Paris'.
    If so, blocks the tool execution and returns a specific error dictionary.
    Otherwise, allows the tool call to proceed by returning None.
    """
    tool_name = tool.name
    agent_name = tool_context.agent_name # Agent attempting the tool call
    print(f"--- Callback: block_paris_tool_guardrail running for tool '{tool_name}' in agent '{agent_name}' ---")
    print(f"--- Callback: Inspecting args: {args} ---")

    # --- Guardrail Logic ---
    target_tool_name = "get_weather_stateful" # Match the function name used by FunctionTool
    blocked_city = "paris"

    # Check if it's the correct tool and the city argument matches the blocked city
    if tool_name == target_tool_name:
        city_argument = args.get("city", "") # Safely get the 'city' argument
        if city_argument and city_argument.lower() == blocked_city:
            print(f"--- Callback: Detected blocked city '{city_argument}'. Blocking tool execution! ---")
            # Optionally update state
            tool_context.state["guardrail_tool_block_triggered"] = True
            print(f"--- Callback: Set state 'guardrail_tool_block_triggered': True ---")

            # Return a dictionary matching the tool's expected output format for errors
            # This dictionary becomes the tool's result, skipping the actual tool run.
            return {
                "status": "error",
                "error_message": f"Policy restriction: Weather checks for '{city_argument.capitalize()}' are currently disabled by a tool guardrail."
            }
        else:
             print(f"--- Callback: City '{city_argument}' is allowed for tool '{tool_name}'. ---")
    else:
        print(f"--- Callback: Tool '{tool_name}' is not the target tool. Allowing. ---")


    # If the checks above didn't return a dictionary, allow the tool to execute
    print(f"--- Callback: Allowing tool '{tool_name}' to proceed. ---")
    return None # Returning None allows the actual tool function to run

print("✅ block_paris_tool_guardrail function defined.")
2. Update Root Agent to Use Both Callbacks

We redefine the root agent again (weather_agent_v6_tool_guardrail), this time adding the before_tool_callback parameter alongside the before_model_callback from Step 5.

Self-Contained Execution Note: Similar to Step 5, ensure all prerequisites (sub-agents, tools, before_model_callback) are defined or available in the execution context before defining this agent.


# @title 2. Update Root Agent with BOTH Callbacks (Self-Contained)

# --- Ensure Prerequisites are Defined ---
# (Include or ensure execution of definitions for: Agent, LiteLlm, Runner, ToolContext,
#  MODEL constants, say_hello, say_goodbye, greeting_agent, farewell_agent,
#  get_weather_stateful, block_keyword_guardrail, block_paris_tool_guardrail)

# --- Redefine Sub-Agents (Ensures they exist in this context) ---
greeting_agent = None
try:
    # Use a defined model constant
    greeting_agent = Agent(
        model=MODEL_GEMINI_2_0_FLASH,
        name="greeting_agent", # Keep original name for consistency
        instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting using the 'say_hello' tool. Do nothing else.",
        description="Handles simple greetings and hellos using the 'say_hello' tool.",
        tools=[say_hello],
    )
    print(f"✅ Sub-Agent '{greeting_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Greeting agent. Check Model/API Key ({greeting_agent.model}). Error: {e}")

farewell_agent = None
try:
    # Use a defined model constant
    farewell_agent = Agent(
        model=MODEL_GEMINI_2_0_FLASH,
        name="farewell_agent", # Keep original name
        instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message using the 'say_goodbye' tool. Do not perform any other actions.",
        description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
        tools=[say_goodbye],
    )
    print(f"✅ Sub-Agent '{farewell_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Farewell agent. Check Model/API Key ({farewell_agent.model}). Error: {e}")

# --- Define the Root Agent with Both Callbacks ---
root_agent_tool_guardrail = None
runner_root_tool_guardrail = None

if ('greeting_agent' in globals() and greeting_agent and
    'farewell_agent' in globals() and farewell_agent and
    'get_weather_stateful' in globals() and
    'block_keyword_guardrail' in globals() and
    'block_paris_tool_guardrail' in globals()):

    root_agent_model = MODEL_GEMINI_2_0_FLASH

    root_agent_tool_guardrail = Agent(
        name="weather_agent_v6_tool_guardrail", # New version name
        model=root_agent_model,
        description="Main agent: Handles weather, delegates, includes input AND tool guardrails.",
        instruction="You are the main Weather Agent. Provide weather using 'get_weather_stateful'. "
                    "Delegate greetings to 'greeting_agent' and farewells to 'farewell_agent'. "
                    "Handle only weather, greetings, and farewells.",
        tools=[get_weather_stateful],
        sub_agents=[greeting_agent, farewell_agent],
        output_key="last_weather_report",
        before_model_callback=block_keyword_guardrail, # Keep model guardrail
        before_tool_callback=block_paris_tool_guardrail # <<< Add tool guardrail
    )
    print(f"✅ Root Agent '{root_agent_tool_guardrail.name}' created with BOTH callbacks.")

    # --- Create Runner, Using SAME Stateful Session Service ---
    if 'session_service_stateful' in globals():
        runner_root_tool_guardrail = Runner(
            agent=root_agent_tool_guardrail,
            app_name=APP_NAME,
            session_service=session_service_stateful # <<< Use the service from Step 4/5
        )
        print(f"✅ Runner created for tool guardrail agent '{runner_root_tool_guardrail.agent.name}', using stateful session service.")
    else:
        print("❌ Cannot create runner. 'session_service_stateful' from Step 4/5 is missing.")

else:
    print("❌ Cannot create root agent with tool guardrail. Prerequisites missing.")
3. Interact to Test the Tool Guardrail

Let's test the interaction flow, again using the same stateful session (SESSION_ID_STATEFUL) from the previous steps.

Request weather for "New York": Passes both callbacks, tool executes (using Fahrenheit preference from state).
Request weather for "Paris": Passes before_model_callback. LLM decides to call get_weather_stateful(city='Paris'). before_tool_callback intercepts, blocks the tool, and returns the error dictionary. Agent relays this error.
Request weather for "London": Passes both callbacks, tool executes normally.

# @title 3. Interact to Test the Tool Argument Guardrail
import asyncio # Ensure asyncio is imported

# Ensure the runner for the tool guardrail agent is available
if 'runner_root_tool_guardrail' in globals() and runner_root_tool_guardrail:
    # Define the main async function for the tool guardrail test conversation.
    # The 'await' keywords INSIDE this function are necessary for async operations.
    async def run_tool_guardrail_test():
        print("\n--- Testing Tool Argument Guardrail ('Paris' blocked) ---")

        # Use the runner for the agent with both callbacks and the existing stateful session
        # Define a helper lambda for cleaner interaction calls
        interaction_func = lambda query: call_agent_async(query,
                                                         runner_root_tool_guardrail,
                                                         USER_ID_STATEFUL, # Use existing user ID
                                                         SESSION_ID_STATEFUL # Use existing session ID
                                                        )
        # 1. Allowed city (Should pass both callbacks, use Fahrenheit state)
        print("--- Turn 1: Requesting weather in New York (expect allowed) ---")
        await interaction_func("What's the weather in New York?")

        # 2. Blocked city (Should pass model callback, but be blocked by tool callback)
        print("\n--- Turn 2: Requesting weather in Paris (expect blocked by tool guardrail) ---")
        await interaction_func("How about Paris?") # Tool callback should intercept this

        # 3. Another allowed city (Should work normally again)
        print("\n--- Turn 3: Requesting weather in London (expect allowed) ---")
        await interaction_func("Tell me the weather in London.")

    # --- Execute the `run_tool_guardrail_test` async function ---
    # Choose ONE of the methods below based on your environment.

    # METHOD 1: Direct await (Default for Notebooks/Async REPLs)
    # If your environment supports top-level await (like Colab/Jupyter notebooks),
    # it means an event loop is already running, so you can directly await the function.
    print("Attempting execution using 'await' (default for notebooks)...")
    await run_tool_guardrail_test()

    # METHOD 2: asyncio.run (For Standard Python Scripts [.py])
    # If running this code as a standard Python script from your terminal,
    # the script context is synchronous. `asyncio.run()` is needed to
    # create and manage an event loop to execute your async function.
    # To use this method:
    # 1. Comment out the `await run_tool_guardrail_test()` line above.
    # 2. Uncomment the following block:
    """
    import asyncio
    if __name__ == "__main__": # Ensures this runs only when script is executed directly
        print("Executing using 'asyncio.run()' (for standard Python scripts)...")
        try:
            # This creates an event loop, runs your async function, and closes the loop.
            asyncio.run(run_tool_guardrail_test())
        except Exception as e:
            print(f"An error occurred: {e}")
    """

    # --- Inspect final session state after the conversation ---
    # This block runs after either execution method completes.
    # Optional: Check state for the tool block trigger flag
    print("\n--- Inspecting Final Session State (After Tool Guardrail Test) ---")
    # Use the session service instance associated with this stateful session
    final_session = await session_service_stateful.get_session(app_name=APP_NAME,
                                                         user_id=USER_ID_STATEFUL,
                                                         session_id= SESSION_ID_STATEFUL)
    if final_session:
        # Use .get() for safer access
        print(f"Tool Guardrail Triggered Flag: {final_session.state.get('guardrail_tool_block_triggered', 'Not Set (or False)')}")
        print(f"Last Weather Report: {final_session.state.get('last_weather_report', 'Not Set')}") # Should be London weather if successful
        print(f"Temperature Unit: {final_session.state.get('user_preference_temperature_unit', 'Not Set')}") # Should be Fahrenheit
        # print(f"Full State Dict: {final_session.state}") # For detailed view
    else:
        print("\n❌ Error: Could not retrieve final session state.")

else:
    print("\n⚠️ Skipping tool guardrail test. Runner ('runner_root_tool_guardrail') is not available.")
Analyze the output:

New York: The before_model_callback allows the request. The LLM requests get_weather_stateful. The before_tool_callback runs, inspects the args ({'city': 'New York'}), sees it's not "Paris", prints "Allowing tool..." and returns None. The actual get_weather_stateful function executes, reads "Fahrenheit" from state, and returns the weather report. The agent relays this, and it gets saved via output_key.
Paris: The before_model_callback allows the request. The LLM requests get_weather_stateful(city='Paris'). The before_tool_callback runs, inspects the args, detects "Paris", prints "Blocking tool execution!", sets the state flag, and returns the error dictionary {'status': 'error', 'error_message': 'Policy restriction...'}. The actual get_weather_stateful function is never executed. The agent receives the error dictionary as if it were the tool's output and formulates a response based on that error message.
London: Behaves like New York, passing both callbacks and executing the tool successfully. The new London weather report overwrites the last_weather_report in the state.
You've now added a crucial safety layer controlling not just what reaches the LLM, but also how the agent's tools can be used based on the specific arguments generated by the LLM. Callbacks like before_model_callback and before_tool_callback are essential for building robust, safe, and policy-compliant agent applications.

Conclusion: Your Agent Team is Ready!¶
Congratulations! You've successfully journeyed from building a single, basic weather agent to constructing a sophisticated, multi-agent team using the Agent Development Kit (ADK).

Let's recap what you've accomplished:

You started with a fundamental agent equipped with a single tool (get_weather).
You explored ADK's multi-model flexibility using LiteLLM, running the same core logic with different LLMs like Gemini, GPT-4o, and Claude.
You embraced modularity by creating specialized sub-agents (greeting_agent, farewell_agent) and enabling automatic delegation from a root agent.
You gave your agents memory using Session State, allowing them to remember user preferences (temperature_unit) and past interactions (output_key).
You implemented crucial safety guardrails using both before_model_callback (blocking specific input keywords) and before_tool_callback (blocking tool execution based on arguments like the city "Paris").
Through building this progressive Weather Bot team, you've gained hands-on experience with core ADK concepts essential for developing complex, intelligent applications.

Key Takeaways:

Agents & Tools: The fundamental building blocks for defining capabilities and reasoning. Clear instructions and docstrings are paramount.
Runners & Session Services: The engine and memory management system that orchestrate agent execution and maintain conversational context.
Delegation: Designing multi-agent teams allows for specialization, modularity, and better management of complex tasks. Agent description is key for auto-flow.
Session State (ToolContext, output_key): Essential for creating context-aware, personalized, and multi-turn conversational agents.
Callbacks (before_model, before_tool): Powerful hooks for implementing safety, validation, policy enforcement, and dynamic modifications before critical operations (LLM calls or tool execution).
Flexibility (LiteLlm): ADK empowers you to choose the best LLM for the job, balancing performance, cost, and features.


# Session and Memory
Introduction to Conversational Context: Session, State, and Memory¶
Why Context Matters¶
Meaningful, multi-turn conversations require agents to understand context. Just like humans, they need to recall the conversation history: what's been said and done to maintain continuity and avoid repetition. The Agent Development Kit (ADK) provides structured ways to manage this context through Session, State, and Memory.

Core Concepts¶
Think of different instances of your conversations with the agent as distinct conversation threads, potentially drawing upon long-term knowledge.

Session: The Current Conversation Thread

Represents a single, ongoing interaction between a user and your agent system.
Contains the chronological sequence of messages and actions taken by the agent (referred to Events) during that specific interaction.
A Session can also hold temporary data (State) relevant only during this conversation.
State (session.state): Data Within the Current Conversation

Data stored within a specific Session.
Used to manage information relevant only to the current, active conversation thread (e.g., items in a shopping cart during this chat, user preferences mentioned in this session).
Memory: Searchable, Cross-Session Information

Represents a store of information that might span multiple past sessions or include external data sources.
It acts as a knowledge base the agent can search to recall information or context beyond the immediate conversation.
Managing Context: Services¶
ADK provides services to manage these concepts:

SessionService: Manages the different conversation threads (Session objects)

Handles the lifecycle: creating, retrieving, updating (appending Events, modifying State), and deleting individual Sessions.
MemoryService: Manages the Long-Term Knowledge Store (Memory)

Handles ingesting information (often from completed Sessions) into the long-term store.
Provides methods to search this stored knowledge based on queries.
Implementations: ADK offers different implementations for both SessionService and MemoryService, allowing you to choose the storage backend that best fits your application's needs. Notably, in-memory implementations are provided for both services; these are designed specifically for local testing and fast development. It's important to remember that all data stored using these in-memory options (sessions, state, or long-term knowledge) is lost when your application restarts. For persistence and scalability beyond local testing, ADK also offers cloud-based and database service options.

In Summary:

Session & State: Focus on the current interaction – the history and data of the single, active conversation. Managed primarily by a SessionService.
Memory: Focuses on the past and external information – a searchable archive potentially spanning across conversations. Managed by a MemoryService.

Session: Tracking Individual Conversations¶
Following our Introduction, let's dive into the Session. Think back to the idea of a "conversation thread." Just like you wouldn't start every text message from scratch, agents need context regarding the ongoing interaction. Session is the ADK object designed specifically to track and manage these individual conversation threads.

The Session Object¶
When a user starts interacting with your agent, the SessionService creates a Session object (google.adk.sessions.Session). This object acts as the container holding everything related to that one specific chat thread. Here are its key properties:

Identification (id, appName, userId): Unique labels for the conversation.
id: A unique identifier for this specific conversation thread, essential for retrieving it later. A SessionService object can handle multiple Session(s). This field identifies which particular session object are we referring to. For example, "test_id_modification".
app_name: Identifies which agent application this conversation belongs to. For example, "id_modifier_workflow".
userId: Links the conversation to a particular user.
History (events): A chronological sequence of all interactions (Event objects – user messages, agent responses, tool actions) that have occurred within this specific thread.
Session State (state): A place to store temporary data relevant only to this specific, ongoing conversation. This acts as a scratchpad for the agent during the interaction. We will cover how to use and manage state in detail in the next section.
Activity Tracking (lastUpdateTime): A timestamp indicating the last time an event occurred in this conversation thread.
Example: Examining Session Properties¶

Python
Java

 from google.adk.sessions import InMemorySessionService, Session

 # Create a simple session to examine its properties
 temp_service = InMemorySessionService()
 example_session = await temp_service.create_session(
     app_name="my_app",
     user_id="example_user",
     state={"initial_key": "initial_value"} # State can be initialized
 )

 print(f"--- Examining Session Properties ---")
 print(f"ID (`id`):                {example_session.id}")
 print(f"Application Name (`app_name`): {example_session.app_name}")
 print(f"User ID (`user_id`):         {example_session.user_id}")
 print(f"State (`state`):           {example_session.state}") # Note: Only shows initial state here
 print(f"Events (`events`):         {example_session.events}") # Initially empty
 print(f"Last Update (`last_update_time`): {example_session.last_update_time:.2f}")
 print(f"---------------------------------")

 # Clean up (optional for this example)
 temp_service = await temp_service.delete_session(app_name=example_session.app_name,
                             user_id=example_session.user_id, session_id=example_session.id)
 print("The final status of temp_service - ", temp_service)

(Note: The state shown above is only the initial state. State updates happen via events, as discussed in the State section.)

Managing Sessions with a SessionService¶
As seen above, you don't typically create or manage Session objects directly. Instead, you use a SessionService. This service acts as the central manager responsible for the entire lifecycle of your conversation sessions.

Its core responsibilities include:

Starting New Conversations: Creating fresh Session objects when a user begins an interaction.
Resuming Existing Conversations: Retrieving a specific Session (using its ID) so the agent can continue where it left off.
Saving Progress: Appending new interactions (Event objects) to a session's history. This is also the mechanism through which session state gets updated (more in the State section).
Listing Conversations: Finding the active session threads for a particular user and application.
Cleaning Up: Deleting Session objects and their associated data when conversations are finished or no longer needed.
SessionService Implementations¶
ADK provides different SessionService implementations, allowing you to choose the storage backend that best suits your needs:

InMemorySessionService

How it works: Stores all session data directly in the application's memory.
Persistence: None. All conversation data is lost if the application restarts.
Requires: Nothing extra.
Best for: Quick development, local testing, examples, and scenarios where long-term persistence isn't required.

Python
Java

 from google.adk.sessions import InMemorySessionService
 session_service = InMemorySessionService()

VertexAiSessionService

How it works: Uses Google Cloud Vertex AI infrastructure via API calls for session management.
Persistence: Yes. Data is managed reliably and scalably via Vertex AI Agent Engine.
Requires:
A Google Cloud project (pip install vertexai)
A Google Cloud storage bucket that can be configured by this step.
A Reasoning Engine resource name/ID that can setup following this tutorial.
If you do not have a Google Cloud project and you want to try the VertexAiSessionService for free, see how to try Session and Memory for free.
Best for: Scalable production applications deployed on Google Cloud, especially when integrating with other Vertex AI features.

Python
Java

# Requires: pip install google-adk[vertexai]
# Plus GCP setup and authentication
from google.adk.sessions import VertexAiSessionService

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
# The app_name used with this service should be the Reasoning Engine ID or name
REASONING_ENGINE_APP_NAME = "projects/your-gcp-project-id/locations/us-central1/reasoningEngines/your-engine-id"

session_service = VertexAiSessionService(project=PROJECT_ID, location=LOCATION)
# Use REASONING_ENGINE_APP_NAME when calling service methods, e.g.:
# session_service = await session_service.create_session(app_name=REASONING_ENGINE_APP_NAME, ...)

DatabaseSessionService

python_only

How it works: Connects to a relational database (e.g., PostgreSQL, MySQL, SQLite) to store session data persistently in tables.
Persistence: Yes. Data survives application restarts.
Requires: A configured database.
Best for: Applications needing reliable, persistent storage that you manage yourself.

from google.adk.sessions import DatabaseSessionService
# Example using a local SQLite file:
db_url = "sqlite:///./my_agent_data.db"
session_service = DatabaseSessionService(db_url=db_url)
Choosing the right SessionService is key to defining how your agent's conversation history and temporary data are stored and persist.

The Session Lifecycle¶
Session lifecycle

Here’s a simplified flow of how Session and SessionService work together during a conversation turn:

Start or Resume: Your application needs to use the SessionService to either create_session (for a new chat) or use an existing session id.
Context Provided: The Runner gets the appropriate Session object from the appropriate service method, providing the agent with access to the corresponding Session's state and events.
Agent Processing: The user prompts the agent with a query. The agent analyzes the query and potentially the session state and events history to determine the response.
Response & State Update: The agent generates a response (and potentially flags data to be updated in the state). The Runner packages this as an Event.
Save Interaction: The Runner calls sessionService.append_event(session, event) with the session and the new event as the arguments. The service adds the Event to the history and updates the session's state in storage based on information within the event. The session's last_update_time also get updated.
Ready for Next: The agent's response goes to the user. The updated Session is now stored by the SessionService, ready for the next turn (which restarts the cycle at step 1, usually with the continuation of the conversation in the current session).
End Conversation: When the conversation is over, your application calls sessionService.delete_session(...) to clean up the stored session data if it is no longer required.
This cycle highlights how the SessionService ensures conversational continuity by managing the history and state associated with each Session object.

State: The Session's Scratchpad¶
Within each Session (our conversation thread), the state attribute acts like the agent's dedicated scratchpad for that specific interaction. While session.events holds the full history, session.state is where the agent stores and updates dynamic details needed during the conversation.

What is session.state?¶
Conceptually, session.state is a collection (dictionary or Map) holding key-value pairs. It's designed for information the agent needs to recall or track to make the current conversation effective:

Personalize Interaction: Remember user preferences mentioned earlier (e.g., 'user_preference_theme': 'dark').
Track Task Progress: Keep tabs on steps in a multi-turn process (e.g., 'booking_step': 'confirm_payment').
Accumulate Information: Build lists or summaries (e.g., 'shopping_cart_items': ['book', 'pen']).
Make Informed Decisions: Store flags or values influencing the next response (e.g., 'user_is_authenticated': True).
Key Characteristics of State¶
Structure: Serializable Key-Value Pairs

Data is stored as key: value.
Keys: Always strings (str). Use clear names (e.g., 'departure_city', 'user:language_preference').
Values: Must be serializable. This means they can be easily saved and loaded by the SessionService. Stick to basic types in the specific languages (Python/ Java) like strings, numbers, booleans, and simple lists or dictionaries containing only these basic types. (See API documentation for precise details).
⚠️ Avoid Complex Objects: Do not store non-serializable objects (custom class instances, functions, connections, etc.) directly in the state. Store simple identifiers if needed, and retrieve the complex object elsewhere.
Mutability: It Changes

The contents of the state are expected to change as the conversation evolves.
Persistence: Depends on SessionService

Whether state survives application restarts depends on your chosen service:
InMemorySessionService: Not Persistent. State is lost on restart.
DatabaseSessionService / VertexAiSessionService: Persistent. State is saved reliably.
Note

The specific parameters or method names for the primitives may vary slightly by SDK language (e.g., session.state['current_intent'] = 'book_flight' in Python, session.state().put("current_intent", "book_flight) in Java). Refer to the language-specific API documentation for details.

Organizing State with Prefixes: Scope Matters¶
Prefixes on state keys define their scope and persistence behavior, especially with persistent services:

No Prefix (Session State):

Scope: Specific to the current session (id).
Persistence: Only persists if the SessionService is persistent (Database, VertexAI).
Use Cases: Tracking progress within the current task (e.g., 'current_booking_step'), temporary flags for this interaction (e.g., 'needs_clarification').
Example: session.state['current_intent'] = 'book_flight'
user: Prefix (User State):

Scope: Tied to the user_id, shared across all sessions for that user (within the same app_name).
Persistence: Persistent with Database or VertexAI. (Stored by InMemory but lost on restart).
Use Cases: User preferences (e.g., 'user:theme'), profile details (e.g., 'user:name').
Example: session.state['user:preferred_language'] = 'fr'
app: Prefix (App State):

Scope: Tied to the app_name, shared across all users and sessions for that application.
Persistence: Persistent with Database or VertexAI. (Stored by InMemory but lost on restart).
Use Cases: Global settings (e.g., 'app:api_endpoint'), shared templates.
Example: session.state['app:global_discount_code'] = 'SAVE10'
temp: Prefix (Temporary Invocation State):

Scope: Specific to the current invocation (the entire process from an agent receiving user input to generating the final output for that input).
Persistence: Not Persistent. Discarded after the invocation completes and does not carry over to the next one.
Use Cases: Storing intermediate calculations, flags, or data passed between tool calls within a single invocation.
When Not to Use: For information that must persist across different invocations, such as user preferences, conversation history summaries, or accumulated data.
Example: session.state['temp:raw_api_response'] = {...}
Sub-Agents and Invocation Context

When a parent agent calls a sub-agent (e.g., using SequentialAgent or ParallelAgent), it passes its InvocationContext to the sub-agent. This means the entire chain of agent calls shares the same invocation ID and, therefore, the same temp: state.

How the Agent Sees It: Your agent code interacts with the combined state through the single session.state collection (dict/ Map). The SessionService handles fetching/merging state from the correct underlying storage based on prefixes.

Accessing Session State in Agent Instructions¶
When working with LlmAgent instances, you can directly inject session state values into the agent's instruction string using a simple templating syntax. This allows you to create dynamic and context-aware instructions without relying solely on natural language directives.

Using {key} Templating¶
To inject a value from the session state, enclose the key of the desired state variable within curly braces: {key}. The framework will automatically replace this placeholder with the corresponding value from session.state before passing the instruction to the LLM.

Example:


from google.adk.agents import LlmAgent

story_generator = LlmAgent(
    name="StoryGenerator",
    model="gemini-2.0-flash",
    instruction="""Write a short story about a cat, focusing on the theme: {topic}."""
)

# Assuming session.state['topic'] is set to "friendship", the LLM 
# will receive the following instruction:
# "Write a short story about a cat, focusing on the theme: friendship."
Important Considerations¶
Key Existence: Ensure that the key you reference in the instruction string exists in the session.state. If the key is missing, the agent will throw an error. To use a key that may or may not be present, you can include a question mark (?) after the key (e.g. {topic?}).
Data Types: The value associated with the key should be a string or a type that can be easily converted to a string.
Escaping: If you need to use literal curly braces in your instruction (e.g., for JSON formatting), you'll need to escape them.
Bypassing State Injection with InstructionProvider¶
In some cases, you might want to use {{ and }} literally in your instructions without triggering the state injection mechanism. For example, you might be writing instructions for an agent that helps with a templating language that uses the same syntax.

To achieve this, you can provide a function to the instruction parameter instead of a string. This function is called an InstructionProvider. When you use an InstructionProvider, the ADK will not attempt to inject state, and your instruction string will be passed to the model as-is.

The InstructionProvider function receives a ReadonlyContext object, which you can use to access session state or other contextual information if you need to build the instruction dynamically.


Python

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

# This is an InstructionProvider
def my_instruction_provider(context: ReadonlyContext) -> str:
    # You can optionally use the context to build the instruction
    # For this example, we'll return a static string with literal braces.
    return "This is an instruction with {{literal_braces}} that will not be replaced."

agent = LlmAgent(
    model="gemini-2.0-flash",
    name="template_helper_agent",
    instruction=my_instruction_provider
)

If you want to both use an InstructionProvider and inject state into your instructions, you can use the inject_session_state utility function.


Python

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils import instructions_utils

async def my_dynamic_instruction_provider(context: ReadonlyContext) -> str:
    template = "This is a {adjective} instruction with {{literal_braces}}."
    # This will inject the 'adjective' state variable but leave the literal braces.
    return await instructions_utils.inject_session_state(template, context)

agent = LlmAgent(
    model="gemini-2.0-flash",
    name="dynamic_template_helper_agent",
    instruction=my_dynamic_instruction_provider
)

Benefits of Direct Injection

Clarity: Makes it explicit which parts of the instruction are dynamic and based on session state.
Reliability: Avoids relying on the LLM to correctly interpret natural language instructions to access state.
Maintainability: Simplifies instruction strings and reduces the risk of errors when updating state variable names.
Relation to Other State Access Methods

This direct injection method is specific to LlmAgent instructions. Refer to the following section for more information on other state access methods.

How State is Updated: Recommended Methods¶
The Right Way to Modify State

When you need to change the session state, the correct and safest method is to directly modify the state object on the Context provided to your function (e.g., callback_context.state['my_key'] = 'new_value'). This is considered "direct state manipulation" in the right way, as the framework automatically tracks these changes.

This is critically different from directly modifying the state on a Session object you retrieve from the SessionService (e.g., my_session.state['my_key'] = 'new_value'). You should avoid this, as it bypasses the ADK's event tracking and can lead to lost data. The "Warning" section at the end of this page has more details on this important distinction.

State should always be updated as part of adding an Event to the session history using session_service.append_event(). This ensures changes are tracked, persistence works correctly, and updates are thread-safe.

1. The Easy Way: output_key (for Agent Text Responses)

This is the simplest method for saving an agent's final text response directly into the state. When defining your LlmAgent, specify the output_key:


Python
Java

from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner
from google.genai.types import Content, Part

# Define agent with output_key
greeting_agent = LlmAgent(
    name="Greeter",
    model="gemini-2.0-flash", # Use a valid model
    instruction="Generate a short, friendly greeting.",
    output_key="last_greeting" # Save response to state['last_greeting']
)

# --- Setup Runner and Session ---
app_name, user_id, session_id = "state_app", "user1", "session1"
session_service = InMemorySessionService()
runner = Runner(
    agent=greeting_agent,
    app_name=app_name,
    session_service=session_service
)
session = await session_service.create_session(app_name=app_name,
                                    user_id=user_id,
                                    session_id=session_id)
print(f"Initial state: {session.state}")

# --- Run the Agent ---
# Runner handles calling append_event, which uses the output_key
# to automatically create the state_delta.
user_message = Content(parts=[Part(text="Hello")])
for event in runner.run(user_id=user_id,
                        session_id=session_id,
                        new_message=user_message):
    if event.is_final_response():
      print(f"Agent responded.") # Response text is also in event.content

# --- Check Updated State ---
updated_session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
print(f"State after agent run: {updated_session.state}")
# Expected output might include: {'last_greeting': 'Hello there! How can I help you today?'}

Behind the scenes, the Runner uses the output_key to create the necessary EventActions with a state_delta and calls append_event.

2. The Standard Way: EventActions.state_delta (for Complex Updates)

For more complex scenarios (updating multiple keys, non-string values, specific scopes like user: or app:, or updates not tied directly to the agent's final text), you manually construct the state_delta within EventActions.


Python
Java

from google.adk.sessions import InMemorySessionService, Session
from google.adk.events import Event, EventActions
from google.genai.types import Part, Content
import time

# --- Setup ---
session_service = InMemorySessionService()
app_name, user_id, session_id = "state_app_manual", "user2", "session2"
session = await session_service.create_session(
    app_name=app_name,
    user_id=user_id,
    session_id=session_id,
    state={"user:login_count": 0, "task_status": "idle"}
)
print(f"Initial state: {session.state}")

# --- Define State Changes ---
current_time = time.time()
state_changes = {
    "task_status": "active",              # Update session state
    "user:login_count": session.state.get("user:login_count", 0) + 1, # Update user state
    "user:last_login_ts": current_time,   # Add user state
    "temp:validation_needed": True        # Add temporary state (will be discarded)
}

# --- Create Event with Actions ---
actions_with_update = EventActions(state_delta=state_changes)
# This event might represent an internal system action, not just an agent response
system_event = Event(
    invocation_id="inv_login_update",
    author="system", # Or 'agent', 'tool' etc.
    actions=actions_with_update,
    timestamp=current_time
    # content might be None or represent the action taken
)

# --- Append the Event (This updates the state) ---
await session_service.append_event(session, system_event)
print("`append_event` called with explicit state delta.")

# --- Check Updated State ---
updated_session = await session_service.get_session(app_name=app_name,
                                            user_id=user_id,
                                            session_id=session_id)
print(f"State after event: {updated_session.state}")
# Expected: {'user:login_count': 1, 'task_status': 'active', 'user:last_login_ts': <timestamp>}
# Note: 'temp:validation_needed' is NOT present.

3. Via CallbackContext or ToolContext (Recommended for Callbacks and Tools)

Modifying state within agent callbacks (e.g., on_before_agent_call, on_after_agent_call) or tool functions is best done using the state attribute of the CallbackContext or ToolContext provided to your function.

callback_context.state['my_key'] = my_value
tool_context.state['my_key'] = my_value
These context objects are specifically designed to manage state changes within their respective execution scopes. When you modify context.state, the ADK framework ensures that these changes are automatically captured and correctly routed into the EventActions.state_delta for the event being generated by the callback or tool. This delta is then processed by the SessionService when the event is appended, ensuring proper persistence and tracking.

This method abstracts away the manual creation of EventActions and state_delta for most common state update scenarios within callbacks and tools, making your code cleaner and less error-prone.

For more comprehensive details on context objects, refer to the Context documentation.


Python
Java

# In an agent callback or tool function
from google.adk.agents import CallbackContext # or ToolContext

def my_callback_or_tool_function(context: CallbackContext, # Or ToolContext
                                 # ... other parameters ...
                                ):
    # Update existing state
    count = context.state.get("user_action_count", 0)
    context.state["user_action_count"] = count + 1

    # Add new state
    context.state["temp:last_operation_status"] = "success"

    # State changes are automatically part of the event's state_delta
    # ... rest of callback/tool logic ...

What append_event Does:

Adds the Event to session.events.
Reads the state_delta from the event's actions.
Applies these changes to the state managed by the SessionService, correctly handling prefixes and persistence based on the service type.
Updates the session's last_update_time.
Ensures thread-safety for concurrent updates.
⚠️ A Warning About Direct State Modification¶
Avoid directly modifying the session.state collection (dictionary/Map) on a Session object that was obtained directly from the SessionService (e.g., via session_service.get_session() or session_service.create_session()) outside of the managed lifecycle of an agent invocation (i.e., not through a CallbackContext or ToolContext). For example, code like retrieved_session = await session_service.get_session(...); retrieved_session.state['key'] = value is problematic.

State modifications within callbacks or tools using CallbackContext.state or ToolContext.state are the correct way to ensure changes are tracked, as these context objects handle the necessary integration with the event system.

Why direct modification (outside of contexts) is strongly discouraged:

Bypasses Event History: The change isn't recorded as an Event, losing auditability.
Breaks Persistence: Changes made this way will likely NOT be saved by DatabaseSessionService or VertexAiSessionService. They rely on append_event to trigger saving.
Not Thread-Safe: Can lead to race conditions and lost updates.
Ignores Timestamps/Logic: Doesn't update last_update_time or trigger related event logic.
Recommendation: Stick to updating state via output_key, EventActions.state_delta (when manually creating events), or by modifying the state property of CallbackContext or ToolContext objects when within their respective scopes. These methods ensure reliable, trackable, and persistent state management. Use direct access to session.state (from a SessionService-retrieved session) only for reading state.

Best Practices for State Design Recap¶
Minimalism: Store only essential, dynamic data.
Serialization: Use basic, serializable types.
Descriptive Keys & Prefixes: Use clear names and appropriate prefixes (user:, app:, temp:, or none).
Shallow Structures: Avoid deep nesting where possible.
Standard Update Flow: Rely on append_event.

Memory: Long-Term Knowledge with MemoryService¶
python_only

We've seen how Session tracks the history (events) and temporary data (state) for a single, ongoing conversation. But what if an agent needs to recall information from past conversations or access external knowledge bases? This is where the concept of Long-Term Knowledge and the MemoryService come into play.

Think of it this way:

Session / State: Like your short-term memory during one specific chat.
Long-Term Knowledge (MemoryService): Like a searchable archive or knowledge library the agent can consult, potentially containing information from many past chats or other sources.
The MemoryService Role¶
The BaseMemoryService defines the interface for managing this searchable, long-term knowledge store. Its primary responsibilities are:

Ingesting Information (add_session_to_memory): Taking the contents of a (usually completed) Session and adding relevant information to the long-term knowledge store.
Searching Information (search_memory): Allowing an agent (typically via a Tool) to query the knowledge store and retrieve relevant snippets or context based on a search query.
Choosing the Right Memory Service¶
The ADK offers two distinct MemoryService implementations, each tailored to different use cases. Use the table below to decide which is the best fit for your agent.

Feature	InMemoryMemoryService	[NEW!] VertexAiMemoryBankService
Persistence	None (data is lost on restart)	Yes (Managed by Vertex AI)
Primary Use Case	Prototyping, local development, and simple testing.	Building meaningful, evolving memories from user conversations.
Memory Extraction	Stores full conversation	Extracts meaningful information from conversations and consolidates it with existing memories (powered by LLM)
Search Capability	Basic keyword matching.	Advanced semantic search.
Setup Complexity	None. It's the default.	Low. Requires an Agent Engine in Vertex AI.
Dependencies	None.	Google Cloud Project, Vertex AI API
When to use it	When you want to search across multiple sessions’ chat histories for prototyping.	When you want your agent to remember and learn from past interactions.
In-Memory Memory¶
The InMemoryMemoryService stores session information in the application's memory and performs basic keyword matching for searches. It requires no setup and is best for prototyping and simple testing scenarios where persistence isn't required.


from google.adk.memory import InMemoryMemoryService
memory_service = InMemoryMemoryService()
Example: Adding and Searching Memory

This example demonstrates the basic flow using the InMemoryMemoryService for simplicity.

Full Code
Vertex AI Memory Bank¶
The VertexAiMemoryBankService connects your agent to Vertex AI Memory Bank, a fully managed Google Cloud service that provides sophisticated, persistent memory capabilities for conversational agents.

How It Works¶
The service automatically handles two key operations:

Generating Memories: At the end of a conversation, the ADK sends the session's events to the Memory Bank, which intelligently processes and stores the information as "memories."
Retrieving Memories: Your agent code can issue a search query against the Memory Bank to retrieve relevant memories from past conversations.
Prerequisites¶
Before you can use this feature, you must have:

A Google Cloud Project: With the Vertex AI API enabled.
An Agent Engine: You need to create an Agent Engine in Vertex AI. This will provide you with the Agent Engine ID required for configuration.
Authentication: Ensure your local environment is authenticated to access Google Cloud services. The simplest way is to run:

gcloud auth application-default login
Environment Variables: The service requires your Google Cloud Project ID and Location. Set them as environment variables:

export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="your-gcp-location"
Configuration¶
To connect your agent to the Memory Bank, you use the --memory_service_uri flag when starting the ADK server (adk web or adk api_server). The URI must be in the format agentengine://<agent_engine_id>.

bash

adk web path/to/your/agents_dir --memory_service_uri="agentengine://1234567890"
Or, you can configure your agent to use the Memory Bank by manually instantiating the VertexAiMemoryBankService and passing it to the Runner.


from google.adk.memory import VertexAiMemoryBankService

agent_engine_id = agent_engine.api_resource.name.split("/")[-1]

memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID",
    location="LOCATION",
    agent_engine_id=agent_engine_id
)

runner = adk.Runner(
    ...
    memory_service=memory_service
)
Using Memory in Your Agent¶
With the service configured, the ADK automatically saves session data to the Memory Bank. To make your agent use this memory, you need to call the search_memory method from your agent's code.

This is typically done at the beginning of a turn to fetch relevant context before generating a response.

Example:


from google.adk.agents import Agent
from google.genai import types

class MyAgent(Agent):
    async def run(self, request: types.Content, **kwargs) -> types.Content:
        # Get the user's latest message
        user_query = request.parts[0].text

        # Search the memory for context related to the user's query
        search_result = await self.search_memory(query=user_query)

        # Create a prompt that includes the retrieved memories
        prompt = f"Based on my memory, here's what I recall about your query: {search_result.memories}\n\nNow, please respond to: {user_query}"

        # Call the LLM with the enhanced prompt
        return await self.llm.generate_content_async(prompt)
Advanced Concepts¶
How Memory Works in Practice¶
The memory workflow internally involves these steps:

Session Interaction: A user interacts with an agent via a Session, managed by a SessionService. Events are added, and state might be updated.
Ingestion into Memory: At some point (often when a session is considered complete or has yielded significant information), your application calls memory_service.add_session_to_memory(session). This extracts relevant information from the session's events and adds it to the long-term knowledge store (in-memory dictionary or RAG Corpus).
Later Query: In a different (or the same) session, the user might ask a question requiring past context (e.g., "What did we discuss about project X last week?").
Agent Uses Memory Tool: An agent equipped with a memory-retrieval tool (like the built-in load_memory tool) recognizes the need for past context. It calls the tool, providing a search query (e.g., "discussion project X last week").
Search Execution: The tool internally calls memory_service.search_memory(app_name, user_id, query).
Results Returned: The MemoryService searches its store (using keyword matching or semantic search) and returns relevant snippets as a SearchMemoryResponse containing a list of MemoryResult objects (each potentially holding events from a relevant past session).
Agent Uses Results: The tool returns these results to the agent, usually as part of the context or function response. The agent can then use this retrieved information to formulate its final answer to the user.
Can an agent have access to more than one memory service?¶
Through Standard Configuration: No. The framework (adk web, adk api_server) is designed to be configured with one single memory service at a time via the --memory_service_uri flag. This single service is then provided to the agent and accessed through the built-in self.search_memory() method. From a configuration standpoint, you can only choose one backend (InMemory, VertexAiMemoryBankService) for all agents served by that process.

Within Your Agent's Code: Yes, absolutely. There is nothing preventing you from manually importing and instantiating another memory service directly inside your agent's code. This allows you to access multiple memory sources within a single agent turn.

For example, your agent could use the framework-configured VertexAiMemoryBankService to recall conversational history, and also manually instantiate a InMemoryMemoryService to look up information in a technical manual.

Example: Using Two Memory Services¶
Here’s how you could implement that in your agent's code:


from google.adk.agents import Agent
from google.adk.memory import InMemoryMemoryService, VertexAiMemoryBankService
from google.genai import types

class MultiMemoryAgent(Agent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.memory_service = InMemoryMemoryService()
        # Manually instantiate a second memory service for document lookups
        self.vertexai_memorybank_service = VertexAiMemoryBankService(
            project="PROJECT_ID",
            location="LOCATION",
            agent_engine_id="AGENT_ENGINE_ID"
        )

    async def run(self, request: types.Content, **kwargs) -> types.Content:
        user_query = request.parts[0].text

        # 1. Search conversational history using the framework-provided memory
        #    (This would be InMemoryMemoryService if configured)
        conversation_context = await self.memory_service.search_memory(query=user_query)

        # 2. Search the document knowledge base using the manually created service
        document_context = await self.vertexai_memorybank_service.search_memory(query=user_query)

        # Combine the context from both sources to generate a better response
        prompt = "From our past conversations, I remember:\n"
        prompt += f"{conversation_context.memories}\n\n"
        prompt += "From the technical manuals, I found:\n"
        prompt += f"{document_context.memories}\n\n"
        prompt += f"Based on all this, here is my answer to '{user_query}':"

        return await self.llm.generate_content_async(prompt)

