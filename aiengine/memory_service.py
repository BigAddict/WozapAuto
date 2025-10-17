"""
Memory service for semantic search and context window management.
"""
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from django.db.models import Q
from sentence_transformers import SentenceTransformer
import logging

from .models import ConversationThread, ConversationMessage
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger("aiengine.memory_service")


class MemoryService:
    """
    Service for managing conversation memory with semantic search capabilities.
    """
    
    def __init__(self, thread: ConversationThread, max_context_messages: int = 20):
        """
        Initialize the memory service.
        
        Args:
            thread: ConversationThread instance
            max_context_messages: Maximum number of messages to keep in context
        """
        self.thread = thread
        self.max_context_messages = max_context_messages
        
        # Initialize embedding model with error handling
        self.embedding_model = None
        self.embedding_dimensions = 0
        
        # Try different embedding models in order of preference
        models_to_try = [
            'all-MiniLM-L6-v2',
            'paraphrase-MiniLM-L6-v2', 
            'all-MiniLM-L12-v2',
            'distilbert-base-nli-mean-tokens'
        ]
        
        for model_name in models_to_try:
            try:
                logger.info(f"Trying to initialize embedding model: {model_name}")
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_dimensions = 384  # Most models use 384 dimensions
                logger.info(f"Successfully initialized embedding model: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Failed to initialize {model_name}: {e}")
                continue
        
        if not self.embedding_model:
            logger.error("Failed to initialize any embedding model. Semantic search will be disabled.")
            self.embedding_model = None
            self.embedding_dimensions = 0
        
    def add_message(self, message_type: str, content: str, metadata: Dict[str, Any] = None, token_usage: Dict[str, Any] = None) -> ConversationMessage:
        """
        Add a new message to the conversation with embedding.
        
        Args:
            message_type: Type of message ('human', 'ai', 'system')
            content: Message content
            metadata: Additional metadata
            token_usage: Token usage information (for AI messages)
            
        Returns:
            ConversationMessage instance
        """
        try:
            # Generate embedding for the message if model is available
            embedding = None
            if self.embedding_model:
                try:
                    embedding = self.embedding_model.encode(content).tolist()
                except Exception as e:
                    logger.warning(f"Error generating embedding: {e}")
                    embedding = None
            
            # Extract token usage information
            input_tokens = None
            output_tokens = None
            total_tokens = None
            model_name = None
            
            if token_usage:
                input_tokens = token_usage.get('input_tokens')
                output_tokens = token_usage.get('output_tokens')
                total_tokens = token_usage.get('total_tokens')
                model_name = token_usage.get('model_name')
            
            # Create message
            message = ConversationMessage.objects.create(
                thread=self.thread,
                message_type=message_type,
                content=content,
                embedding=embedding,
                metadata=metadata or {},
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                model_name=model_name
            )
            
            logger.info(f"Added {message_type} message to thread {self.thread.thread_id}")
            return message
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise
    
    def get_relevant_messages(
        self, 
        query: str, 
        limit: int = 10, 
        similarity_threshold: float = 0.7
    ) -> List[ConversationMessage]:
        """
        Get relevant messages using semantic search.
        
        Args:
            query: Search query
            limit: Maximum number of messages to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relevant ConversationMessage instances
        """
        try:
            # If no embedding model, return recent messages
            if not self.embedding_model:
                logger.warning("No embedding model available, returning recent messages")
                return ConversationMessage.objects.filter(
                    thread=self.thread
                ).order_by('-created_at')[:limit]
            
            # Generate embedding for the query
            query_embedding = self.embedding_model.encode(query)
            
            # Get all messages with embeddings
            messages = ConversationMessage.objects.filter(
                thread=self.thread,
                embedding__isnull=False
            ).order_by('-created_at')
            
            if not messages.exists():
                return []
            
            # Calculate similarities
            similarities = []
            for message in messages:
                # Check if embedding exists and is not None
                if message.embedding is not None and len(message.embedding) > 0:
                    try:
                        # Safely convert embeddings to numpy arrays
                        query_vec = np.array(query_embedding, dtype=np.float32)
                        
                        # Handle different embedding formats
                        if isinstance(message.embedding, (list, tuple)):
                            msg_vec = np.array(message.embedding, dtype=np.float32)
                        elif isinstance(message.embedding, np.ndarray):
                            msg_vec = message.embedding.astype(np.float32)
                        else:
                            # Skip if embedding is not in expected format
                            logger.warning(f"Unexpected embedding format for message {message.id}: {type(message.embedding)}")
                            continue
                        
                        # Ensure vectors have the same shape
                        if query_vec.shape != msg_vec.shape:
                            logger.warning(f"Shape mismatch for message {message.id}: query {query_vec.shape} vs message {msg_vec.shape}")
                            continue
                        
                        # Calculate cosine similarity
                        dot_product = np.dot(query_vec, msg_vec)
                        norm_product = np.linalg.norm(query_vec) * np.linalg.norm(msg_vec)
                        
                        if norm_product == 0:
                            similarity = 0.0
                        else:
                            similarity = dot_product / norm_product
                        
                        # Ensure similarity is a scalar
                        similarity = float(similarity)
                        
                        if similarity >= similarity_threshold:
                            similarities.append((message, similarity))
                    except Exception as e:
                        logger.warning(f"Error calculating similarity for message {message.id}: {e}")
                        continue
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [msg for msg, _ in similarities[:limit]]
            
        except Exception as e:
            logger.error(f"Error getting relevant messages: {e}")
            # Fallback to recent messages
            return ConversationMessage.objects.filter(
                thread=self.thread
            ).order_by('-created_at')[:limit]
    
    def get_context_messages(
        self, 
        query: Optional[str] = None,
        include_recent: bool = True,
        include_semantic: bool = True,
        max_messages: Optional[int] = None
    ) -> List[BaseMessage]:
        """
        Get messages for context window, combining recent and semantically relevant messages.
        
        Args:
            query: Optional query for semantic search
            include_recent: Whether to include recent messages
            include_semantic: Whether to include semantically relevant messages
            max_messages: Override max_context_messages
            
        Returns:
            List of LangChain BaseMessage objects
        """
        try:
            max_messages = max_messages or self.max_context_messages
            context_messages = []
            
            # Get recent messages if requested
            if include_recent:
                recent_messages = ConversationMessage.objects.filter(
                    thread=self.thread
                ).order_by('-created_at')[:max_messages // 2]
                
                for msg in recent_messages:
                    if msg.message_type == 'human':
                        context_messages.append(HumanMessage(content=msg.content))
                    elif msg.message_type == 'ai':
                        context_messages.append(AIMessage(content=msg.content))
                    elif msg.message_type == 'system':
                        context_messages.append(SystemMessage(content=msg.content))
            
            # Get semantically relevant messages if query provided
            if include_semantic and query:
                relevant_messages = self.get_relevant_messages(
                    query, 
                    limit=max_messages // 2
                )
                
                for msg in relevant_messages:
                    # Avoid duplicates
                    if not any(existing.content == msg.content for existing in context_messages):
                        if msg.message_type == 'human':
                            context_messages.append(HumanMessage(content=msg.content))
                        elif msg.message_type == 'ai':
                            context_messages.append(AIMessage(content=msg.content))
                        elif msg.message_type == 'system':
                            context_messages.append(SystemMessage(content=msg.content))
            
            # Sort by creation time and limit
            context_messages = context_messages[-max_messages:]
            
            logger.info(f"Retrieved {len(context_messages)} context messages for thread {self.thread.thread_id}")
            return context_messages
            
        except Exception as e:
            logger.error(f"Error getting context messages: {e}")
            return []
    
    def cleanup_old_messages(self, keep_recent: int = 100) -> int:
        """
        Clean up old messages, keeping only the most recent ones.
        
        Args:
            keep_recent: Number of recent messages to keep
            
        Returns:
            Number of messages deleted
        """
        try:
            # Get messages to keep (most recent)
            messages_to_keep = ConversationMessage.objects.filter(
                thread=self.thread
            ).order_by('-created_at')[:keep_recent]
            
            keep_ids = set(messages_to_keep.values_list('id', flat=True))
            
            # Delete older messages
            deleted_count = ConversationMessage.objects.filter(
                thread=self.thread
            ).exclude(id__in=keep_ids).delete()[0]
            
            logger.info(f"Cleaned up {deleted_count} old messages from thread {self.thread.thread_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up messages: {e}")
            return 0
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation.
        
        Returns:
            Dictionary with conversation statistics
        """
        try:
            total_messages = ConversationMessage.objects.filter(thread=self.thread).count()
            human_messages = ConversationMessage.objects.filter(
                thread=self.thread, 
                message_type='human'
            ).count()
            ai_messages = ConversationMessage.objects.filter(
                thread=self.thread, 
                message_type='ai'
            ).count()
            
            first_message = ConversationMessage.objects.filter(
                thread=self.thread
            ).order_by('created_at').first()
            
            last_message = ConversationMessage.objects.filter(
                thread=self.thread
            ).order_by('-created_at').first()
            
            return {
                'total_messages': total_messages,
                'human_messages': human_messages,
                'ai_messages': ai_messages,
                'first_message_at': first_message.created_at if first_message else None,
                'last_message_at': last_message.created_at if last_message else None,
                'thread_id': self.thread.thread_id,
                'remote_jid': self.thread.remote_jid,
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {}
    
    def update_message_embeddings(self) -> int:
        """
        Update embeddings for messages that don't have them.
        
        Returns:
            Number of messages updated
        """
        try:
            # If no embedding model, return 0
            if not self.embedding_model:
                logger.warning("No embedding model available, cannot update embeddings")
                return 0
            
            messages_without_embeddings = ConversationMessage.objects.filter(
                thread=self.thread,
                embedding__isnull=True
            )
            
            updated_count = 0
            for message in messages_without_embeddings:
                try:
                    embedding = self.embedding_model.encode(message.content).tolist()
                    message.embedding = embedding
                    message.save(update_fields=['embedding'])
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Error updating embedding for message {message.id}: {e}")
            
            logger.info(f"Updated embeddings for {updated_count} messages")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating message embeddings: {e}")
            return 0
