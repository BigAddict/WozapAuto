from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

text_formatting_guide = """
# Below is a text formatting guide for whatsapp messages

Italic
To italicize your message, place an underscore on both sides of the text:
_text_

Bold
To bold your message, place an asterisk on both sides of the text:
*text*

Strikethrough
To strikethrough your message, place a tilde on both sides of the text:
~text~

Monospace
To monospace your message, place three backticks on both sides of the text:
```text```

Bulleted list
To add a bulleted list to your message, place an asterisk or hyphen and a space before each word or sentence:
* text
* text
Or
- text
- text

Numbered list
To add a numbered list to your message, place a number, period, and space before each line of text:
1. text
2. text

Quote
To add a quote to your message, place an angle bracket and space before the text:
> text

Inline code
To add inline code to your message, place a backtick on both sides of the message:
`text`
"""

def create_system_instructions(system_prompt: str) -> str:
    """
    Create comprehensive system instructions for the AI agent.
    
    Args:
        system_prompt: The base system prompt from the Agent model
        
    Returns:
        Complete system instructions string
    """
    # Get current time and date
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    system_instructions = f"""
Current time: {current_time}

You are a helpful AI assistant integrated with WhatsApp. You have access to:
- Conversation memory to recall previous discussions
- Knowledge base search to find information from uploaded documents. Always check if it contains info on topics
before providing a not available or not sure response. May contain products too and their prices
- Real-time context about the current conversation

Use the available tools when needed to provide accurate and helpful responses.

You must respond with a JSON object in this exact format:
{{"needs_reply": true, "response_text": "your message here"}}

Rules:
- If the user needs a WhatsApp reply, set needs_reply to true and put the message in response_text
- If a reply is not needed (e.g., info-only webhook or duplicate/invalid input), set needs_reply to false and briefly explain why in response_text
- Always return valid JSON, nothing else

{system_prompt}
{text_formatting_guide}
"""
    
    # Debug logging
    import logging
    logger = logging.getLogger("aiengine.prompts")
    logger.info(f"Created system instructions with base prompt: {system_prompt[:50]}...")
    logger.debug(f"Full system instructions: {system_instructions[:200]}...")
    
    return system_instructions

def create_prompt_template(system_prompt: str) -> ChatPromptTemplate:
    """
    Create the complete prompt template for the agent.
    
    Args:
        system_prompt: The base system prompt from the Agent model
        
    Returns:
        ChatPromptTemplate with system instructions and message placeholder
    """
    system_instructions = create_system_instructions(system_prompt)
    
    return ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        MessagesPlaceholder(variable_name="messages")
    ])
