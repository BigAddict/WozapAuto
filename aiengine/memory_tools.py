"""
Memory search tools for LangGraph agents.
"""
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import logging

logger = logging.getLogger(__name__)

class MemorySearchTool:
    """Tool for searching conversation memory."""
    
    def __init__(self, memory_service):
        self.memory_service = memory_service
    
    def search_memory(self, query: str, limit: int = 10) -> str:
        """
        Search through previous conversation history to find relevant information.
        
        Use this tool when the user asks about something that might have been discussed
        in previous conversations or when you need more context about a topic.
        
        Examples of when to use:
        - User references past conversations ("as we discussed", "you mentioned", "last time")
        - User asks about previous decisions, preferences, or commitments
        - You need context about an ongoing conversation topic
        - Follow-up questions that require conversation history
        
        Args:
            query: The search query to find relevant messages
            limit: Maximum number of messages to return (default: 10)
            
        Returns:
            String containing relevant messages from conversation history
        """
        try:
            logger.info(f"Memory search tool called with query: {query}")
            
            if not self.memory_service:
                logger.warning("Memory service not available")
                return "Memory service not available."
            
            # Get relevant messages using semantic search
            relevant_messages = self.memory_service.get_relevant_messages(
                query=query,
                limit=limit,
                similarity_threshold=0.6  # Lower threshold for tool usage
            )
            
            if not relevant_messages:
                logger.info(f"No relevant messages found for query: {query}")
                return f"No relevant messages found for query: '{query}'"
            
            # Format the results
            result_parts = [f"Found {len(relevant_messages)} relevant messages for '{query}':\n"]
            
            for i, msg in enumerate(relevant_messages, 1):
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M")
                result_parts.append(f"{i}. [{msg.message_type.upper()}] ({timestamp}): {msg.content}")
            
            logger.info(f"Memory search completed: {len(relevant_messages)} results found")
            return "\n".join(result_parts)
            
        except Exception as e:
            logger.error(f"Error in memory search tool: {e}")
            return f"Error searching memory: {str(e)}"
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation thread.
        
        Returns:
            String containing conversation statistics and summary
        """
        try:
            logger.info("Conversation summary tool called")
            
            if not self.memory_service:
                logger.warning("Memory service not available")
                return "Memory service not available."
            
            summary = self.memory_service.get_conversation_summary()
            
            if not summary:
                logger.info("No conversation data available")
                return "No conversation data available."
            
            result_parts = [
                f"Conversation Summary:",
                f"- Total messages: {summary.get('total_messages', 0)}",
                f"- Human messages: {summary.get('human_messages', 0)}",
                f"- AI messages: {summary.get('ai_messages', 0)}",
                f"- Conversation started: {summary.get('first_message_at', 'Unknown')}",
                f"- Last activity: {summary.get('last_message_at', 'Unknown')}"
            ]
            
            logger.info("Conversation summary completed")
            return "\n".join(result_parts)
            
        except Exception as e:
            logger.error(f"Error in conversation summary tool: {e}")
            return f"Error getting conversation summary: {str(e)}"
    
    def get_tools(self) -> List:
        """Get all memory tools for the agent."""
        # Create tool instances
        search_tool = tool(self.search_memory)
        summary_tool = tool(self.get_conversation_summary)
        return [search_tool, summary_tool]
