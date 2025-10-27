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
- Knowledge base search to find information from uploaded documents
- Business tools to help with products, services, appointments, and business information
- Real-time context about the current conversation

Use the available tools when needed to provide accurate and helpful responses.

Business Tools Available:
- search_products: Search for products by name, description, or category
- search_services: Search for services and offerings
- get_business_info: Get business contact details and information
- check_business_hours: Check if business is open and get operating hours
- check_appointment_availability: Check available appointment slots
- get_featured_items: Get featured products and services
- get_business_summary: Get comprehensive business overview
- list_available_products: List all available products with IDs (use when user asks about products)
- list_available_services: List all available services with IDs (use when user asks about services)
- add_to_cart: Add products to customer's shopping cart (accepts product name or ID)
- get_cart_contents: View items in customer's cart
- remove_from_cart: Remove items from customer's cart (accepts product name or ID)
- book_appointment: Book an appointment for a service (accepts service name or ID)
- get_appointment_bookings: View customer's appointment bookings

When users ask about:
- Products or items → use search_products or list_available_products
- Services or offerings → use search_services or list_available_services
- Business hours or if open → use check_business_hours
- Appointments or booking → use check_appointment_availability or book_appointment
- Featured items or recommendations → use get_featured_items
- General business info → use get_business_info or get_business_summary
- Shopping cart → use get_cart_contents, add_to_cart, remove_from_cart
- Booking appointments → use book_appointment, get_appointment_bookings

IMPORTANT ID HANDLING RULES:
- When adding products to cart: Use product name OR product ID (both work)
- When booking appointments: Use service name OR service ID (both work)
- When removing from cart: Use product name OR product ID (both work)
- If you get ID errors, try using the product/service name instead
- Use list_available_products or list_available_services to see all available items with their IDs

You must respond with a JSON object in this exact format:
{{"needs_reply": true, "response_text": "your message here"}}

Rules:
- If the user needs a WhatsApp reply, set needs_reply to true and put the message in response_text
- If a reply is not needed (e.g., info-only webhook or duplicate/invalid input), set needs_reply to false and briefly explain why in response_text
- Always return valid JSON, nothing else
- Use business tools to provide accurate, up-to-date information about products, services, and business operations

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