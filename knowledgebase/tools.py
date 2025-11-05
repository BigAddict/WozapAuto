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
    
    def search_knowledge_base(self, query: str, top_k: int = None) -> str:
        """
        Search user's knowledge base for relevant information.
        
        Use this tool when the user asks about specific information that might be
        in their uploaded documents or knowledge base. This tool searches through
        the user's personal knowledge base to find relevant information.
        
        Examples of when to use:
        - User asks about content from documents they uploaded
        - Questions about products, prices, policies, or procedures documented in files
        - Requests for specific information that isn't general knowledge
        - Follow-up questions about previously discussed document content
        
        Args:
            query: The search query to find relevant information
            top_k: Maximum number of results to return (default: uses user settings)
            
        Returns:
            String containing relevant information from knowledge base
        """
        try:
            logger.info(f"KB Tool called by user {self.user.username} with query: {query}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('knowledge_base_used', True)
            
            # Get user settings for similarity threshold and max chunks
            settings = self.kb_service.settings
            similarity_threshold = settings.similarity_threshold if settings else 0.5
            max_chunks = settings.max_chunks_in_context if settings else 3
            
            # Use top_k from settings if not provided
            if top_k is None:
                top_k = settings.top_k_results if settings else 5
            
            # Search knowledge base (get more results for filtering)
            results = self.kb_service.search_knowledge_base(self.user, query, top_k)
            
            if not results:
                logger.info(f"No knowledge base results found for query: {query}")
                return f"No relevant information found in your knowledge base for: '{query}'\n\nTip: Try rephrasing your question or using different keywords."
            
            # Filter by similarity threshold
            filtered_results = [
                r for r in results 
                if getattr(r, 'similarity_score', 0.0) >= similarity_threshold
            ]
            
            if not filtered_results:
                logger.info(f"No results met similarity threshold {similarity_threshold} for query: {query}")
                return f"No sufficiently relevant information found in your knowledge base for: '{query}'\n\nThe search found some results, but they weren't closely related enough to be helpful. Try rephrasing your question."
            
            # Limit to max_chunks_in_context
            filtered_results = filtered_results[:max_chunks]
            
            # Format results
            result_parts = [f"Found {len(filtered_results)} relevant document(s) for '{query}':\n"]
            
            for i, result in enumerate(filtered_results, 1):
                similarity_score = getattr(result, 'similarity_score', 0.0)
                result_parts.append(
                    f"{i}. From {result.original_filename} (relevance: {similarity_score:.2f}):\n"
                    f"{result.chunk_text}\n"
                )
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"KB search completed: {len(filtered_results)} results found (threshold: {similarity_threshold})")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in knowledge base search: {e}")
            return f"Error searching knowledge base: {str(e)}"
    
    def get_tool(self):
        """Get the LangChain tool instance."""
        return tool(self.search_knowledge_base)
