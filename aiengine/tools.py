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
    PURPOSE:
        Returns the current date and time in UTC.

    WHEN TO USE:
        Use this tool only when the user asks about the current time, date, or day.

    WHEN NOT TO USE:
        Do not use this tool for tasks unrelated to date or time.

    INPUTS:
        None

    OUTPUTS:
        str: Human-readable current date and time in UTC format: 'YYYY-MM-DD HH:MM:SS'

    NOTES:
        Always returns UTC time. Convert to local timezone if required for the user.
    """
    try:
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Tool get_current_time called, returning: {current_time}")
        return f"The current date and time is: {current_time}"
    except Exception as e:
        logger.error(f"Error in get_current_time tool: {e}")
        return "Sorry, I couldn't get the current time."

def send_whatsapp_message(message: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    PURPOSE:
        Sends a WhatsApp message to a specific user using the Evolution API.

    WHEN TO USE:
        Use to reply or initiate messages with customers.

    WHEN NOT TO USE:
        Do not use for group messages or messages to yourself.
        Do not send empty or repeated messages.

    INPUTS:
        message (str): Text message to send.
        tool_context (ToolContext): Must contain:
            - user:instance_name (str): Required instance name.
            - user:remote_jid (str): Recipient phone number.
            - temp:reply_to_message_id (str, optional): ID to reply to.

    OUTPUTS:
        Dict[str, Any]: {
            'success': bool,
            'message': str,
            'response': Any (optional),
            'error': str (optional)
        }

    NOTES:
        Always include the instance name. This tool interfaces with Evolution API.
    """
    try:
        instance_name = tool_context.state.get('user:instance_name')
        reply_to_message_id = tool_context.state.get('temp:reply_to_message_id')
        if not instance_name:
            return {"success": False, "error": "Instance name missing", "message": "Cannot send message without instance name."}
        if not message.strip():
            return {"success": False, "error": "Empty message", "message": "Cannot send an empty message."}
        number = tool_context.state.get('user:remote_jid')
        if not number.strip():
            return {"success": False, "error": "Phone number missing", "message": "Cannot send message without a phone number."}
        success, response = evolution_api_service.send_text_message(instance_name=instance_name, number=number, message=message, reply_to_message_id=reply_to_message_id)
        if success:
            logger.info(f"Message sent to {number} via {instance_name}")
            return {"success": True, "message": f"Message sent to {number}", "response": response}
        else:
            return {"success": False, "error": f"API failed: {response}", "message": f"Failed to send message to {number}."}
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        return {"success": False, "error": str(e), "message": "Error sending WhatsApp message."}

def send_group_message(message: str, tool_context: ToolContext, mentions_everyone: bool = False, mentions: List[str] = []) -> Dict[str, Any]:
    """
    PURPOSE:
        Sends a message to a WhatsApp group.

    WHEN TO USE:
        Only for group messages.

    WHEN NOT TO USE:
        Do not use for individual messages.

    INPUTS:
        message (str): Text to send.
        tool_context (ToolContext): Context containing instance and remote JID.
        mentions_everyone (bool): Mention all group members.
        mentions (List[str]): Specific user IDs to mention.

    OUTPUTS:
        Dict[str, Any]: { 'success': bool, 'results': Any, 'message': str, 'error': Optional[str] }

    NOTES:
        Requires instance_name and remote_jid in context.
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
                    "quoted": {"key": {"id": reply_to_message_id}} if reply_to_message_id else None,
                    "mentionsEveryOne": mentions_everyone,
                    "mentioned": mentions
                }
            )
            if success:
                return {"success": True, "results": response, "message": "Group message sent successfully."}
    except Exception as e:
        logger.error(f"Error in send_group_message: {e}")
        return {"success": False, "error": str(e), "message": "Error sending group message."}

def check_conversation_messages(tool_context: ToolContext, page: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
    """
    PURPOSE:
        Retrieve past conversation messages from a customer.

    WHEN TO USE:
        Use before referencing past messages.

    WHEN NOT TO USE:
        Do not use for real-time sending.

    INPUTS:
        tool_context (ToolContext): Must contain instance_name and remote_jid.
        page (int, optional): Page of results.
        offset (int, optional): Offset in results.

    OUTPUTS:
        Dict[str, Any]: { 'success': bool, 'results': List[dict], 'message': str, 'error': Optional[str] }
    """
    try:
        instance_name = tool_context.state.get('user:instance_name')
        remote_jid = tool_context.state.get('user:remote_jid')
        success, response = evolution_api_service.send_post_request(endpoint=f"/chat/findMessages/{instance_name}", data={"remoteJid": remote_jid, "page": page, "offset": offset})
        if success:
            return {"success": True, "results": response, "message": "Messages retrieved successfully."}
    except Exception as e:
        logger.error(f"Error in check_conversation_messages: {e}")
        return {"success": False, "error": str(e), "message": "Error retrieving messages."}

def get_group_name(tool_context: ToolContext) -> Dict[str, Any]:
    """
    PURPOSE:
        Retrieve the name of a WhatsApp group.

    WHEN TO USE:
        Only when identifying group chats.

    WHEN NOT TO USE:
        Do not use for individual chats.

    INPUTS:
        tool_context (ToolContext): Must contain instance_name and remote_jid.

    OUTPUTS:
        Dict[str, Any]: { 'success': bool, 'results': Any, 'message': str, 'error': Optional[str] }
    """
    try:
        instance_name = tool_context.state.get('user:instance_name')
        remote_jid = tool_context.state.get('user:remote_jid')
        success, response = evolution_api_service.send_get_request(endpoint=f"/group/findGroupInfos/{instance_name}?groupJid={remote_jid}")
        if success:
            return {"success": True, "results": response, "message": "Group info retrieved successfully."}
    except Exception as e:
        logger.error(f"Error in get_group_name: {e}")
        return {"success": False, "error": str(e), "message": "Error retrieving group info."}

def retrieve_knowledge(query: str, top_k: int, tool_context: ToolContext) -> Dict[str, Any]:
    """
    PURPOSE:
        Retrieve the most relevant knowledge base items for a given query.

    WHEN TO USE:
        Use before answering user questions that require factual or policy-based knowledge.

    WHEN NOT TO USE:
        Do not use for casual conversation or opinion-based responses.

    INPUTS:
        query (str): Natural language search query.
        top_k (int): Number of top results (5-20 recommended).
        tool_context (ToolContext): Must contain instance_name.

    OUTPUTS:
        Dict[str, Any]: { 'success': bool, 'results': List[dict], 'message': str, 'error': Optional[str] }
    """
    try:
        url = f"{get_env_variable('SIT_URL')}/aiengine/retrieve-knowledge/"
        instance_name = tool_context.state.get('user:instance_name')
        payload = {"query": query, "top_k": top_k, "instance_name": instance_name}
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Error in retrieve_knowledge: {e}")
        return {"success": False, "error": str(e), "message": "Error retrieving knowledge base."}

class ToolManager:
    """Manages available tools for the AI Agent"""
    def __init__(self) -> None:
        self._tools: Dict[str, Callable] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool("get_current_time", get_current_time)
        # Intentionally NOT registering send_whatsapp_message. Delivery is handled by server code
        # after parsing the agent's JSON response (AgentResponse schema).
        self.register_tool("retrieve_knowledge", retrieve_knowledge)
        self.register_tool("check_conversation_messages", check_conversation_messages)

        logger.info(f"Registered {len(self._tools)} tools")

    def register_tool(self, name:str, tool_func: Callable) -> None:
        if not callable(tool_func):
            raise ValueError(f"Tool function {name} is not callable")
        self._tools[name] = tool_func
        logger.info(f"Registered tool: {name}")

    def unregister_tool(self, name:str) -> bool:
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        else:
            logger.warning(f"Tool not found: {name}")
            return False

    def get_tool(self, name:str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_all_tools(self) -> List[Callable]:
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_tool_count(self) -> int:
        return len(self._tools)

tool_manager = ToolManager()