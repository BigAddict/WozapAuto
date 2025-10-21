"""
Knowledge Base Tools for LangChain v3 Agent Integration.
"""
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import logging

from .service import KnowledgeBaseService

logger = logging.getLogger("knowledgebase.tools")


class KnowledgeBaseTool:
    """User-scoped knowledge base tool for LangChain agents."""
    
    def __init__(self, user, callback=None):
        """
        Initialize knowledge base tool for a specific user.
        
        Args:
            user: Django User instance
            callback: Optional callback function to track tool usage
        """
        self.user = user
        self.kb_service = KnowledgeBaseService(user=user)
        self.callback = callback
        
        logger.info(f"Initialized KnowledgeBaseTool for user: {user.username}")
    
    def search_knowledge_base(self, query: str, top_k: int = 3) -> str:
        """
        Search user's knowledge base for relevant information.
        
        Use this tool when the user asks about specific information that might be
        in their uploaded documents or knowledge base. This tool searches through
        the user's personal knowledge base to find relevant information.
        
        Args:
            query: The search query to find relevant information
            top_k: Maximum number of results to return (default: 3)
            
        Returns:
            String containing relevant information from knowledge base
        """
        try:
            logger.info(f"KB Tool called by user {self.user.username} with query: {query}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('knowledge_base_used', True)
            
            # Search knowledge base
            results = self.kb_service.search_knowledge_base(self.user, query, top_k)
            
            if not results:
                logger.info(f"No knowledge base results found for query: {query}")
                return f"No relevant information found in your knowledge base for: '{query}'"
            
            # Format results
            result_parts = [f"Found {len(results)} relevant documents for '{query}':\n"]
            
            for i, result in enumerate(results, 1):
                similarity_score = getattr(result, 'similarity_score', 0.0)
                result_parts.append(
                    f"{i}. From {result.original_filename} (relevance: {similarity_score:.2f}):\n"
                    f"{result.chunk_text}\n"
                )
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"KB search completed: {len(results)} results found")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in knowledge base search: {e}")
            return f"Error searching knowledge base: {str(e)}"
    
    def get_tool(self):
        """Get the LangChain tool instance."""
        return tool(self.search_knowledge_base)
