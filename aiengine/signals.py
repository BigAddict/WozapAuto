"""
AI Engine app signals.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ConversationCheckpoint
import logging

logger = logging.getLogger(__name__)

MAX_CHECKPOINTS_PER_THREAD = 20


@receiver(post_save, sender=ConversationCheckpoint)
def limit_checkpoints_per_thread(sender, instance, created, **kwargs):
    """
    Ensure a thread doesn't exceed MAX_CHECKPOINTS_PER_THREAD checkpoints.
    Deletes the oldest checkpoints if the limit is exceeded.
    """
    if not created:
        # Only process newly created checkpoints
        return
    
    thread = instance.thread
    checkpoint_count = ConversationCheckpoint.objects.filter(thread=thread).count()
    
    if checkpoint_count > MAX_CHECKPOINTS_PER_THREAD:
        # Get all checkpoints for this thread, ordered by creation time (oldest first)
        checkpoints = ConversationCheckpoint.objects.filter(
            thread=thread
        ).order_by('created_at')
        
        # Calculate how many to delete
        checkpoints_to_delete = checkpoint_count - MAX_CHECKPOINTS_PER_THREAD
        
        # Get the IDs of the oldest checkpoints to delete (can't use slice with delete())
        old_checkpoint_ids = list(
            checkpoints.values_list('id', flat=True)[:checkpoints_to_delete]
        )
        old_checkpoint_checkpoint_ids = list(
            checkpoints.values_list('checkpoint_id', flat=True)[:checkpoints_to_delete]
        )
        
        # Delete the oldest checkpoints by their primary keys
        deleted_count, _ = ConversationCheckpoint.objects.filter(
            id__in=old_checkpoint_ids
        ).delete()
        
        logger.info(
            f"Deleted {deleted_count} old checkpoints for thread {thread.thread_id}. "
            f"Remaining: {MAX_CHECKPOINTS_PER_THREAD} checkpoints. "
            f"Deleted checkpoint IDs: {old_checkpoint_checkpoint_ids[:5]}{'...' if len(old_checkpoint_checkpoint_ids) > 5 else ''}"
        )
