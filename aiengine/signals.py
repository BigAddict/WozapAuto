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
        
        # Get the oldest checkpoints to delete
        old_checkpoints = checkpoints[:checkpoints_to_delete]
        
        # Delete the oldest checkpoints
        deleted_count = old_checkpoints.count()
        old_checkpoint_ids = list(old_checkpoints.values_list('checkpoint_id', flat=True))
        old_checkpoints.delete()
        
        logger.info(
            f"Deleted {deleted_count} old checkpoints for thread {thread.thread_id}. "
            f"Remaining: {MAX_CHECKPOINTS_PER_THREAD} checkpoints. "
            f"Deleted checkpoint IDs: {old_checkpoint_ids[:5]}{'...' if len(old_checkpoint_ids) > 5 else ''}"
        )
