from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timezone
import logging

from connections.services import evolution_api_service

logger = logging.getLogger('aiengine.tools')

def get_current_time() -> str:
    """
    Get the current date and time in UTC timezone.
    
    This tool should be used whenever the user asks about the current time, date, or day.
    It returns the current date and time in a human-readable format.
    
    Returns:
        str: Current date and time in format "The current date and time is: YYYY-MM-DD HH:MM:SS"
    """
    try:
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Tool get_current_time called, returning: {current_time}")
        return f"The current date and time is: {current_time}"
    except Exception as e:
        logger.error(f"Error in get_current_time tool: {e}")
        return "Sorry, I couldn't get the current time."

def send_whatsapp_message(
    message: str,
    number: str,
    instance_name: Optional[str] = None,
    reply_to_message_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a WhatsApp message to a specific phone number using the Evolution API.
    
    This tool should be used whenever the user wants to send a WhatsApp message to someone.
    The instance_name parameter is REQUIRED and must be provided from the conversation context.
    
    Args:
        message (str): The text message to send to the recipient
        number (str): The phone number to send the message to (with country code, without + sign)
        instance_name (Optional[str]): The WhatsApp instance name to send from (REQUIRED)
        reply_to_message_id (Optional[str]): The message ID to reply to (optional)
    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): True if message was sent successfully, False otherwise
            - message (str): Human-readable status message
            - error (str, optional): Error details if success is False
            - response (Any, optional): API response data if success is True
    """
    try:
        # Validate required parameters
        if not instance_name:
            return {
                "success": False,
                "error": "Instance name is required but not provided",
                "message": "I cannot send the message because the instance name is missing. Please check the instance configuration."
            }
        
        if not message or not message.strip():
            return {
                "success": False,
                "error": "Message content is empty",
                "message": "I cannot send an empty message."
            }
        
        if not number or not number.strip():
            return {
                "success": False,
                "error": "Phone number is empty",
                "message": "I cannot send a message without a valid phone number."
            }

        # Make the API request
        success, response = evolution_api_service.send_text_message(
            instance_name=instance_name,
            number=number,
            message=message,
            reply_to_message_id=reply_to_message_id
        )
        
        if success:
            logger.info(f"Successfully sent WhatsApp message to {number} via instance {instance_name}")
            return {
                "success": True,
                "message": f"Message sent successfully to {number}",
                "response": response
            }
        else:
            logger.error(f"Failed to send WhatsApp message to {number}: {response}")
            return {
                "success": False,
                "error": f"API request failed: {response}",
                "message": f"I was unable to send the message to {number}. The API request failed. Please check the instance configuration and try again."
            }
            
    except Exception as e:
        logger.error(f"Error sending whatsapp message: {e}")
        return {
            "success": False,
            "error": f"Exception occurred: {str(e)}",
            "message": f"I encountered an error while trying to send the message: {str(e)}. Please check the instance configuration and try again."
        }


class ToolManager:
    """Manages available tools for the AI Agent"""
    def __init__(self) -> None:
        self._tools: Dict[str, Callable] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool("get_current_time", get_current_time)
        self.register_tool("send_whatsapp_message", send_whatsapp_message)

        logger.info(f"Registered {len(self._tools)} tools")

    def register_tool(self, name:str, tool_func: Callable) -> None:
        """
        Register a new tool with the tool manager
        """
        if not callable(tool_func):
            raise ValueError(f"Tool function {name} is not callable")

        self._tools[name] = tool_func
        logger.info(f"Registered tool: {name}")
    
    def unregister_tool(self, name:str) -> bool:
        """
        Unregister a tool from the tool manager
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        else:
            logger.warning(f"Tool not found: {name}")
            return False
    
    def get_tool(self, name:str) -> Optional[Callable]:
        """
        Get a tool from the tool manager
        """
        return self._tools.get(name)

    def get_all_tools(self) -> List[Callable]:
        """
        Get all tools from the tool manager
        """
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """
        Get all tool names from the tool manager
        """
        return list(self._tools.keys())

    def get_tool_count(self) -> int:
        return len(self._tools)

tool_manager = ToolManager()