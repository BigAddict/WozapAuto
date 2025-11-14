"""
Custom LangGraph checkpointer that uses Django database for persistent storage.
"""
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from typing import Any, Dict, Optional, Sequence, Iterator
from langchain_core.runnables import RunnableConfig
from django.contrib.auth.models import User
from datetime import datetime, timezone
import uuid

from .models import ConversationThread, ConversationCheckpoint
import logging

logger = logging.getLogger(__name__)


class DatabaseCheckpointSaver(BaseCheckpointSaver):
    """
    A checkpointer that saves conversation state to Django database.
    """
    
    def __init__(self, user: User, agent_id: int, remote_jid: str):
        """
        Initialize the database checkpointer.
        
        Args:
            user: Django User instance
            agent_id: ID of the Agent model
            remote_jid: WhatsApp contact/group ID
        """
        self.user = user
        self.agent_id = agent_id
        self.remote_jid = remote_jid
        self.thread_id = f"{user.id}_{remote_jid}"
        
        # Get or create conversation thread
        self.thread, created = ConversationThread.objects.get_or_create(
            thread_id=self.thread_id,
            defaults={
                'user': user,
                'agent_id': agent_id,
                'remote_jid': remote_jid,
            }
        )
        
        if created:
            logger.info(f"Created new conversation thread: {self.thread_id}")
        else:
            logger.info(f"Using existing conversation thread: {self.thread_id}")

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Get the latest checkpoint for this thread."""
        try:
            checkpoint = ConversationCheckpoint.objects.filter(
                thread=self.thread
            ).order_by('-created_at').first()
            
            if not checkpoint:
                return None
                
            checkpoint_data = checkpoint.checkpoint_data
            return CheckpointTuple(
                config=config,
                checkpoint=Checkpoint(
                    v=checkpoint_data.get('v', 1),
                    id=checkpoint.checkpoint_id,
                    ts=checkpoint.created_at.isoformat(),
                    channel_values=checkpoint_data.get('channel_values', {}),
                    channel_versions=checkpoint_data.get('channel_versions', {}),
                    versions_seen=checkpoint_data.get('versions_seen', {}),
                    pending_sends=checkpoint_data.get('pending_sends', []),
                ),
                metadata=CheckpointMetadata(
                    source="database",
                    step=checkpoint_data.get('step', 0),
                    writes=checkpoint_data.get('writes', {}),
                    parents=checkpoint_data.get('parents', {}),
                ),
            )
        except Exception as e:
            logger.error(f"Error getting checkpoint tuple: {e}")
            return None

    def list(
        self,
        config: Optional[RunnableConfig] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints for this thread."""
        try:
            queryset = ConversationCheckpoint.objects.filter(thread=self.thread)
            
            if before:
                if isinstance(before, str):
                    # Find checkpoint by ID
                    before_checkpoint = ConversationCheckpoint.objects.filter(
                        checkpoint_id=before
                    ).first()
                    if before_checkpoint:
                        queryset = queryset.filter(created_at__lt=before_checkpoint.created_at)
                else:
                    # Find checkpoint by timestamp
                    queryset = queryset.filter(created_at__lt=before)
            
            queryset = queryset.order_by('-created_at')
            
            if limit:
                queryset = queryset[:limit]
            
            checkpoints = []
            for checkpoint in queryset:
                checkpoint_data = checkpoint.checkpoint_data
                checkpoints.append(CheckpointTuple(
                    config=config,
                    checkpoint=Checkpoint(
                        v=checkpoint_data.get('v', 1),
                        id=checkpoint.checkpoint_id,
                        ts=checkpoint.created_at.isoformat(),
                        channel_values=checkpoint_data.get('channel_values', {}),
                        channel_versions=checkpoint_data.get('channel_versions', {}),
                        versions_seen=checkpoint_data.get('versions_seen', {}),
                        pending_sends=checkpoint_data.get('pending_sends', []),
                    ),
                    metadata=CheckpointMetadata(
                        source="database",
                        step=checkpoint_data.get('step', 0),
                        writes=checkpoint_data.get('writes', {}),
                        parents=checkpoint_data.get('parents', {}),
                    ),
                ))
            
            for checkpoint_tuple in checkpoints:
                yield checkpoint_tuple
            
        except Exception as e:
            logger.error(f"Error listing checkpoints: {e}")
            return

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, int],
    ) -> RunnableConfig:
        """Save a new checkpoint to the database."""
        try:
            # Handle checkpoint ID properly
            checkpoint_id = None
            if hasattr(checkpoint, 'id') and checkpoint.id:
                checkpoint_id = checkpoint.id
            elif isinstance(checkpoint, dict) and 'id' in checkpoint:
                checkpoint_id = checkpoint['id']
            else:
                checkpoint_id = str(uuid.uuid4())
            
            # Safely extract checkpoint data with JSON serialization
            def serialize_for_json(obj):
                """Safely serialize objects for JSON storage."""
                if obj is None:
                    return None
                elif isinstance(obj, (str, int, float, bool)):
                    return obj
                elif isinstance(obj, (list, tuple)):
                    return [serialize_for_json(item) for item in obj]
                elif isinstance(obj, dict):
                    return {str(k): serialize_for_json(v) for k, v in obj.items()}
                elif hasattr(obj, '__dict__'):
                    # For objects, try to serialize their dict representation
                    try:
                        return serialize_for_json(obj.__dict__)
                    except:
                        return str(obj)
                else:
                    return str(obj)
            
            # Extract checkpoint data with safe serialization
            channel_values = getattr(checkpoint, 'channel_values', {}) if hasattr(checkpoint, 'channel_values') else checkpoint.get('channel_values', {})
            pending_sends = getattr(checkpoint, 'pending_sends', []) if hasattr(checkpoint, 'pending_sends') else checkpoint.get('pending_sends', [])
            
            checkpoint_data = {
                'v': getattr(checkpoint, 'v', 1) if hasattr(checkpoint, 'v') else checkpoint.get('v', 1),
                'channel_values': serialize_for_json(channel_values),
                'channel_versions': getattr(checkpoint, 'channel_versions', {}) if hasattr(checkpoint, 'channel_versions') else checkpoint.get('channel_versions', {}),
                'versions_seen': getattr(checkpoint, 'versions_seen', {}) if hasattr(checkpoint, 'versions_seen') else checkpoint.get('versions_seen', {}),
                'pending_sends': serialize_for_json(pending_sends),
                'step': getattr(metadata, 'step', 0) if hasattr(metadata, 'step') else metadata.get('step', 0),
                'writes': getattr(metadata, 'writes', {}) if hasattr(metadata, 'writes') else metadata.get('writes', {}),
                'parents': getattr(metadata, 'parents', {}) if hasattr(metadata, 'parents') else metadata.get('parents', {}),
            }
            
            # Create or update checkpoint
            ConversationCheckpoint.objects.update_or_create(
                checkpoint_id=checkpoint_id,
                defaults={
                    'thread': self.thread,
                    'checkpoint_data': checkpoint_data,
                }
            )
            
            # Update thread timestamp
            self.thread.updated_at = datetime.now(timezone.utc)
            self.thread.save(update_fields=['updated_at'])
            
            return config
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            # Don't raise the error to prevent webhook failure
            return config

    def get(self, config: RunnableConfig) -> Optional[Checkpoint]:
        """Get the latest checkpoint for this thread."""
        try:
            checkpoint = ConversationCheckpoint.objects.filter(
                thread=self.thread
            ).order_by('-created_at').first()
            
            if not checkpoint:
                return None
                
            checkpoint_data = checkpoint.checkpoint_data
            return Checkpoint(
                v=checkpoint_data.get('v', 1),
                id=checkpoint.checkpoint_id,
                ts=checkpoint.created_at.isoformat(),
                channel_values=checkpoint_data.get('channel_values', {}),
                channel_versions=checkpoint_data.get('channel_versions', {}),
                versions_seen=checkpoint_data.get('versions_seen', {}),
                pending_sends=checkpoint_data.get('pending_sends', []),
            )
        except Exception as e:
            logger.error(f"Error getting checkpoint: {e}")
            return None

    def put_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = '') -> None:
        """Put writes to the checkpoint."""
        try:
            # For now, we'll just log the writes
            # In a full implementation, you might want to store these writes
            logger.info(f"Put writes: {len(writes)} writes for task {task_id}")
        except Exception as e:
            logger.error(f"Error putting writes: {e}")

    def delete_thread(self, thread_id: str) -> None:
        """Delete a thread and all its checkpoints."""
        try:
            # Find the thread
            thread = ConversationThread.objects.filter(thread_id=thread_id).first()
            if thread:
                # Delete all checkpoints for this thread
                ConversationCheckpoint.objects.filter(thread=thread).delete()
                # Delete the thread itself
                thread.delete()
                logger.info(f"Deleted thread {thread_id}")
        except Exception as e:
            logger.error(f"Error deleting thread: {e}")

    def get_tuple_by_id(self, config: RunnableConfig, checkpoint_id: str) -> Optional[CheckpointTuple]:
        """Get a specific checkpoint by ID."""
        try:
            checkpoint = ConversationCheckpoint.objects.filter(
                checkpoint_id=checkpoint_id,
                thread=self.thread
            ).first()
            
            if not checkpoint:
                return None
                
            checkpoint_data = checkpoint.checkpoint_data
            return CheckpointTuple(
                config=config,
                checkpoint=Checkpoint(
                    v=checkpoint_data.get('v', 1),
                    id=checkpoint.checkpoint_id,
                    ts=checkpoint.created_at.isoformat(),
                    channel_values=checkpoint_data.get('channel_values', {}),
                    channel_versions=checkpoint_data.get('channel_versions', {}),
                    versions_seen=checkpoint_data.get('versions_seen', {}),
                    pending_sends=checkpoint_data.get('pending_sends', []),
                ),
                metadata=CheckpointMetadata(
                    source="database",
                    step=checkpoint_data.get('step', 0),
                    writes=checkpoint_data.get('writes', {}),
                    parents=checkpoint_data.get('parents', {}),
                ),
            )
        except Exception as e:
            logger.error(f"Error getting checkpoint by ID: {e}")
            return None
