from typing import Dict, Any, Optional, List, Callable
from google.adk.tools.tool_context import ToolContext
from datetime import datetime, timezone
import logging
import requests

from connections.services import evolution_api_service
from base.env_config import get_env_variable

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
    tool_context: ToolContext
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
        instance_name = tool_context.state.get('user:instance_name')
        reply_to_message_id = tool_context.state.get('temp:reply_to_message_id')
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

        number = tool_context.state.get('user:remote_jid')
        
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

def send_group_message(
    message: str,
    tool_context: ToolContext,
    mentions_everyone: bool = False,
    mentions: List[str] = []
) -> Dict[str, Any]:
    """
    Call this tool to send a message to a group.

    Args:
        message (str): The text message to send to the group.
        tool_context (ToolContext): Tool context to scope the search by.
        mentions_everyone (Optional[bool]): Whether to mention everyone in the group.
        mentions (Optional[List[str]]): The list of user IDs to mention in the group.

    Returns:
        Dict[str, Any]: {
            "success": bool,
            "results": any,
            "message": str
        }
    """
    try:
        instance_name = tool_context.state.get('user:instance_name')
        remote_jid = tool_context.state.get('user:remote_jid')
        reply_to_message_id = tool_context.state.get('temp:reply_to_message_id')

        if mentions_everyone:
            success, response = evolution_api_service.send_post_request(
                endpoint=f"/message/sendText/{instance_name}",
                data={
                    "number": remote_jid,
                    "text": message,
                    "quoted": {
                        "key": {
                            "id": reply_to_message_id
                        }
                    } if reply_to_message_id else None,
                    "mentionsEveryOne": mentions_everyone,
                    "mentioned": mentions
                }
            )
            if success:
                return {
                    "success": True,
                    "results": response
                }
    except Exception as e:
        logger.error(f"Error in send_group_message tool: {e}")
        return {
            "success": False,
            "error": f"Exception occurred: {str(e)}",
            "message": f"I encountered an error while trying to send the group message: {str(e)}. Please check the instance configuration and try again."
        }

def check_conversation_messages(
    tool_context: ToolContext,
    page: Optional[int] = None,
    offset: Optional[int] = None
) -> Dict[str, Any]:
    """
    Call this tool to get the conversation messages of the customer you're chatting with.

    Args:
        tool_context (ToolContext): Tool context to scope the search by.
        page Optional[int]: The page number to get the conversation messages from.
        offset Optional[int]: The offset number to get the conversation messages from.

    Returns:
        Dict[str, Any]: {
            "success": bool,
            "results": [
                {"id": int, "score": float, "content": str, "metadata": dict, "original_filename": str, "chunk_index": int}
            ],
            "message": str
        }
    """
    try:
        instance_name = tool_context.state.get('user:instance_name')
        remote_jid = tool_context.state.get('user:remote_jid')
        success, response = evolution_api_service.send_post_request(
            endpoint=f"/chat/findMessages/{instance_name}",
            data={
                "remoteJid": remote_jid,
                "page": page,
                "offset": offset
            }
        )
        if success:
            return {
                "success": True,
                "results": response
            }
    except Exception as e:
        logger.error(f"Error in check_conversation_messages tool: {e}")
        return {
            "success": False,
            "error": f"Exception occurred: {str(e)}",
            "message": f"I encountered an error while trying to check the conversation messages: {str(e)}. Please check the instance configuration and try again."
        }

def get_group_name(
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Call this tool to get the name of the group you're chatting with.

    Args:
        tool_context (ToolContext): Tool context to scope the search by.

    Returns:
        Dict[str, Any]: {
            "success": bool,
            "results": [
                {"id": int, "score": float, "content": str, "metadata": dict, "original_filename": str, "chunk_index": int}
            ],
            "message": str
        }
    """
    try:
        instance_name = tool_context.state.get('user:instance_name')
        remote_jid = tool_context.state.get('user:remote_jid')
        success, response = evolution_api_service.send_get_request(
            endpoint=f"/group/findGroupInfos/{instance_name}?groupJid={remote_jid}"
        )
        if success:
            return {
                "success": True,
                "results": response
            }
    except Exception as e:
        logger.error(f"Error in get_group_name tool: {e}")
        return {
            "success": False,
            "error": f"Exception occurred: {str(e)}",
            "message": f"I encountered an error while trying to get the group name: {str(e)}. Please check the instance configuration and try again."
        }

def retrieve_knowledge(
    query: str,
    top_k: int,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Retrieve the most relevant knowledge base chunks for the current tenant/user context.
    Use this tool to get the most relevant knowledge base comprising of documents, policies, and FAQs.

    Args:
        query (str): Natural language query to search with.
        top_k (int): Number of results to return (default 5, max 20).
        tool_context (ToolContext): Tool context to scope the search by.

    Returns:
        Dict[str, Any]: {
            "success": bool,
            "results": [
                {"id": int, "score": float, "content": str, "metadata": dict, "original_filename": str, "chunk_index": int}
            ],
            "message": str
        }
    """
    try:
        print(f"\n\nTool called: {query, top_k, tool_context}\n")
        url = f"{get_env_variable('HOST_URL')}/aiengine/retrieve-knowledge/"
        instance_name = tool_context.state.get('user:instance_name')
        payload = {
            "query": query,
            "top_k": top_k,
            "instance_name": instance_name
        }
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Error in retrieve_knowledge tool: {e}")
        return {
            "success": False,
            "error": f"Exception occurred: {str(e)}",
            "message": f"I encountered an error while trying to retrieve the knowledge base: {str(e)}. Please check the instance configuration and try again."
        }

class ToolManager:
    """Manages available tools for the AI Agent"""
    def __init__(self) -> None:
        self._tools: Dict[str, Callable] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool("get_current_time", get_current_time)
        self.register_tool("send_whatsapp_message", send_whatsapp_message)
        self.register_tool("retrieve_knowledge", retrieve_knowledge)
        self.register_tool("check_conversation_messages", check_conversation_messages)

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