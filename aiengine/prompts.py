from datetime import datetime
from django.utils import timezone as django_timezone
import zoneinfo
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Optional

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

def create_system_instructions(system_prompt: str, user=None, business=None) -> str:
    """
    Create comprehensive system instructions for the AI agent.
    
    Args:
        system_prompt: The base system prompt from the Agent model
        user: Optional User object to get timezone preferences
        business: Optional BusinessProfile object to get timezone preferences
        
    Returns:
        Complete system instructions string
    """
    # Get current time in user's timezone
    current_time = _get_user_time(user, business)
    
    system_instructions = f"""
Current time: {current_time}

You are a helpful AI assistant integrated with WhatsApp. 

## Available Tools and When to Use Them

You have access to 3 powerful tools:

1. **search_memory**: Search previous conversation history
   - Use when user references past discussions ("as we discussed", "you mentioned", "last time")
   - Use to maintain conversation continuity
   - Use to recall user preferences or previous decisions
   
2. **get_conversation_summary**: Get conversation statistics
   - Use when user asks about conversation length, message count, or activity
   - Rarely needed unless specifically requested
   
3. **search_knowledge_base**: Search user's uploaded documents
   - **ALWAYS USE FIRST** when user asks about specific information, items, services, or details
   - Use for ANY question that could possibly be answered by documents or files
   - Use for questions about: offerings, prices, policies, procedures, specifications, availability
   - Use when user describes requirements or asks for recommendations
   - **When in doubt, search first** - it's better to search and find nothing than to miss information
   - DO NOT use for: simple greetings, casual chat, general world knowledge, personal opinions

## Tool Usage Strategy

**Priority Order:**
1. For simple greetings/casual conversation: No tools needed - respond directly
2. For recent conversation context: Try search_memory FIRST
3. **For ANY informational queries**: ALWAYS try search_knowledge_base
4. For queries about user's previous questions/discussions: Use search_memory
5. If both memory and KB might be relevant: Use both tools and combine the information

**Critical Rules:**
- When user asks for information, recommendations, or details → SEARCH KNOWLEDGE BASE FIRST
- **Never say "I can't search" or "I don't have access" without actually trying the search_knowledge_base tool**
- If search returns nothing, THEN say no information was found in your documents
- Always try the tool before concluding information isn't available
- Default to searching when uncertain - it's better to search and find nothing than miss information

**Query Optimization:**
- Extract key entities and keywords from user's question
- Use descriptive search terms based on what user asks for
- If a search returns no results, try reformulating with:
  * Synonyms (e.g., "cost" → "price", "help" → "support")
  * Broader terms (e.g., specific model → general category)
  * Just the main concept (e.g., if detailed query fails, try simpler terms)
  * Different phrasing
- For complex questions, break them into smaller searches
- For queries with multiple requirements, try searching by individual aspects first

**Result Validation:**
- Check relevance scores when provided
- If information seems outdated or contradictory, mention it to the user
- If you're unsure about the accuracy, say so honestly
- Cite sources when using information from knowledge base (mention document names)

**Combining Information:**
- When both memory and knowledge base return results, prioritize the most recent and relevant
- If sources contradict, acknowledge both and ask for clarification
- Synthesize information naturally - don't just concatenate tool outputs

## Example Scenarios

**Scenario 1: Information Request**
User: "I need [something] with [specific requirements]"
→ **Correct Action**: Call search_knowledge_base with the key terms and requirements
→ **Wrong Action**: Responding "I can't search" or "I don't have that information" without using the tool

**Scenario 2: Follow-up Query**  
User: "What did we discuss about [topic]?"
→ **Correct Action**: Call search_memory first, then search_knowledge_base if needed
→ Combine results from both sources

**Scenario 3: No KB Results**
User asks for information, search_knowledge_base returns: "No relevant information found"
→ **Correct Response**: "I didn't find specific information about [topic]. Can i connect you to my boss, or I can help you with something else."
→ **Wrong Response**: Saying "I can't search" or "I don't have access" without actually searching first

## Response Format

You must respond with a JSON object in this exact format:
{{"needs_reply": true, "response_text": "your message here"}}

**Rules:**
- If the user needs a WhatsApp reply, set needs_reply to true and put the message in response_text
- If a reply is not needed (e.g., info-only webhook or duplicate/invalid input), set needs_reply to false and briefly explain why in response_text
- Always return valid JSON, nothing else
- Never include the JSON structure in your actual message to the user

## Custom Instructions

{system_prompt}

{text_formatting_guide}
"""
    
    # Debug logging
    import logging
    logger = logging.getLogger("aiengine.prompts")
    logger.info(f"Created system instructions with base prompt: {system_prompt[:50]}...")
    logger.debug(f"Full system instructions: {system_instructions[:200]}...")
    
    return system_instructions


def _get_user_time(user=None, business=None) -> str:
    """
    Get current time formatted in user's timezone.
    
    Args:
        user: Optional User object
        business: Optional BusinessProfile object
        
    Returns:
        Formatted time string in user's timezone
    """
    # Try to get timezone from business profile
    user_timezone = None
    timezone_name = 'UTC'
    
    try:
        if business and hasattr(business, 'timezone'):
            timezone_name = business.timezone
            user_timezone = zoneinfo.ZoneInfo(business.timezone)
        elif user and hasattr(user, 'business_profile'):
            timezone_name = user.business_profile.timezone
            user_timezone = zoneinfo.ZoneInfo(user.business_profile.timezone)
    except (AttributeError, zoneinfo.ZoneInfoNotFoundError) as e:
        import logging
        logger = logging.getLogger("aiengine.prompts")
        logger.warning(f"Could not get user timezone, using UTC: {e}")
        user_timezone = zoneinfo.ZoneInfo('UTC')
        timezone_name = 'UTC'
    
    # If no timezone found, default to UTC
    if not user_timezone:
        user_timezone = zoneinfo.ZoneInfo('UTC')
        timezone_name = 'UTC'
    
    # Get current time in user's timezone
    now = django_timezone.now().astimezone(user_timezone)
    
    # Format: "Monday, January 15, 2024 at 02:30 PM (EAT)"
    time_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Add timezone abbreviation
    tz_abbr = now.strftime("%Z")
    if tz_abbr:
        time_str += f" ({tz_abbr})"
    else:
        time_str += f" ({timezone_name})"
    
    return time_str


def create_prompt_template(system_prompt: str, user=None, business=None) -> ChatPromptTemplate:
    """
    Create the complete prompt template for the agent.
    
    Args:
        system_prompt: The base system prompt from the Agent model
        user: Optional User object to get timezone preferences
        business: Optional BusinessProfile object to get timezone preferences
        
    Returns:
        ChatPromptTemplate with system instructions and message placeholder
    """
    system_instructions = create_system_instructions(system_prompt, user, business)
    
    return ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        MessagesPlaceholder(variable_name="messages")
    ])
